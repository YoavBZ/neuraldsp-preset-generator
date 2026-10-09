"""Freeze and check inputs for the one-time set-3 confirmation.

Preparation reads development distances, preset settings, model files and the split
declaration only. It never opens held-out audio. A prepared manifest does not grant
permission to run: both it and an approved declaration must be committed first.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import importlib.metadata
import inspect
import json
import math
import os
import pathlib
import platform
import plistlib
import shutil
import statistics
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PLAN = ROOT / "docs/set3-heldout-confirmation-plan.md"
AVERAGE = pathlib.Path("~/ndsp-presets/learn/direc/cache/average-fold2.npy").expanduser()
MODEL = pathlib.Path("~/ndsp-presets/learn/direc/models-set3/fold2.pt").expanduser()
DEVELOPMENT = pathlib.Path("~/ndsp-presets/learn/direc/phase2-set3").expanduser()
OUTPUT = pathlib.Path("~/ndsp-presets/learn/direc/phase2-set3-heldout").expanduser()
CODE = ("learn/phase2_set3.py", "learn/set3_confirmation.py", "learn/set3.py",
        "learn/direc.py", "learn/direc_check.py", "learn/di_robustness.py",
        "analysis/aligned.py", "research/render_preset_panel.py")
BAND_SETS = ("recording", "union")
COMPONENT = pathlib.Path("/Library/Audio/Plug-Ins/Components/Morgan Amps Suite.component")


def sha256(path):
    h = hashlib.sha256()
    with pathlib.Path(path).expanduser().open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def source_inventory():
    """All tracked computation sources/config, not only direct imports."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "learn", "analysis", "match", "format",
         "packs", "scripts", "research"], cwd=ROOT, capture_output=True, check=True)
    tracked = [p for p in result.stdout.decode().split("\0")
               if p and pathlib.Path(p).suffix in (".py", ".swift", ".json", ".yaml", ".yml")]
    return tuple(sorted(set(CODE) | set(tracked)))


def runtime_provenance():
    """Inspect local runtime and installed AU without starting a plugin instance."""
    import soundfile as sf
    from match.renderer_au import AudioUnitRenderer

    dependencies = {}
    for name in ("numpy", "scipy", "soundfile", "pyloudnorm", "torch"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ValueError(f"prepare and run in the same torch environment; missing {name}") from exc
    info = plistlib.loads((COMPONENT / "Contents/Info.plist").read_bytes())
    files = {p.relative_to(COMPONENT).as_posix(): sha256(p)
             for p in sorted(COMPONENT.rglob("*")) if p.is_file()}
    if not files:
        raise ValueError("installed Morgan Audio Unit could not be identified")
    compiler = shutil.which("swiftc")
    if compiler is None:
        raise ValueError("Swift compiler is required for the frozen renderer")
    swift = subprocess.run([compiler, "--version"], capture_output=True, text=True, check=True)
    from scripts import _swift

    sdk_root = pathlib.Path("/Library/Developer/CommandLineTools/SDKs")
    defaults = {name: parameter.default for name, parameter in
                inspect.signature(AudioUnitRenderer.__init__).parameters.items()
                if parameter.default is not inspect.Parameter.empty}
    return {
        "python": platform.python_version(), "executable": str(pathlib.Path(sys.executable).resolve()),
        "dependencies": dependencies, "libsndfile": sf.__libsndfile_version__,
        "platform": platform.platform(), "swift": (swift.stdout + swift.stderr).strip(),
        "swift_build": {"compiler": compiler, "flags": list(_swift.FLAGS),
                        "environment": {n: os.environ.get(n, "") for n in _swift.ENVIRONMENT},
                        "sdks": sorted(str(p) for p in sdk_root.glob("MacOSX*.sdk") if not p.is_symlink())},
        "audio_unit": {"path": str(COMPONENT), "identifier": info.get("CFBundleIdentifier"),
                       "version": info.get("CFBundleShortVersionString"),
                       "build": info.get("CFBundleVersion"), "files": files},
        "renderer": {"id": "swift", "defaults": defaults, "process_policy": "reuse",
                     "inference_device": "cpu", "sample_rate": 48000,
                     "storage": "peak-normalized 0.99, FLAC PCM_24", "warmup_per_amp": 1},
    }


def menu_hashes(amps):
    from learn import phase2_set3 as P
    from packs.loader import load_pack

    class Dummy:
        def _stored(self, pack, spec, value):
            return pack.to_stored(spec, value, warnings=[])

    menus = P.menus(load_pack("morgan"), Dummy(), amps=amps)
    return {amp: {name: canonical_hash(settings) for name, settings in menu.items()}
            for amp, menu in menus.items()}


def select_constants(distances, slugs, menus):
    """K1's raw-distance rule, independently for each declared band set.

    Require the same complete development panel for every candidate. Do not choose
    a constant using different subsets when a distance is refused. Ties use names.
    """
    if set(distances) != set(slugs) or len(slugs) != len(set(slugs)):
        raise ValueError("development distances must cover exactly the declared parts")
    constants = {}
    for bs in BAND_SETS:
        constants[bs] = {}
        for amp, names in menus.items():
            values = {name: [] for name in names if name.startswith("factory:")}
            if not values:
                raise ValueError(f"no factory candidates for {amp}")
            for slug in slugs:
                row = distances[slug][f"{bs}|{amp}|measure_A"]
                if set(row) != set(names):
                    raise ValueError(f"development menu mismatch: {slug}, {amp}, {bs}")
                for name in values:
                    value = row[name]
                    if (isinstance(value, bool) or not isinstance(value, (int, float))
                            or not math.isfinite(value) or value < 0):
                        raise ValueError(f"undefined development distance: {slug}, {name}")
                    values[name].append(value)
            medians = {n: statistics.median(v) for n, v in values.items()}
            name = min(medians, key=lambda n: (medians[n], n))
            constants[bs][amp] = {"preset": name, "median_raw_A": medians[name]}
    return constants


def _positive(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value > 0)


def _band_summary(rows, key):
    by_band = {}
    for row in rows:
        if row[key] is not None:
            by_band.setdefault(row["band"], []).append(row[key])
    medians = {b: statistics.median(v) for b, v in by_band.items()}
    values = list(medians.values())
    if not values:
        return None
    observed = abs(sum(values))
    hits = sum(abs(sum(s * v for s, v in zip(signs, values))) >= observed - 1e-12
               for signs in itertools.product((-1, 1), repeat=len(values)))
    return {"band_medians": medians, "band_median_log_ratio": statistics.median(values),
            "sign_flip_p_two_sided": hits / (2 ** len(values)),
            "scorable_parts": sum(len(v) for v in by_band.values())}


def summarize(distances, parts, manifest):
    """Exact gates; refusals cannot disappear from denominators or produce a pass.

    This function reads distance dictionaries, never audio. A caller may report
    available-case statistics for a refused cell, but the cell automatically fails.
    """
    parts = list(parts.values()) if isinstance(parts, dict) else list(parts)
    if set(distances) != {p["slug"] for p in parts} or not parts:
        raise ValueError("confirmation distances must cover exactly the declared parts")
    output = {}
    for bs in BAND_SETS:
        for amp in manifest["amps"]:
            names = set(manifest["menus"][amp])
            constant = manifest["constants"][bs][amp]["preset"]
            if constant not in names or not constant.startswith("factory:"):
                raise ValueError("constant is outside the frozen factory menu")
            rows = []
            for part in parts:
                data = distances[part["slug"]]
                choose = data[f"{bs}|{amp}|net_A"]
                evaluate = data[f"{bs}|{amp}|measure_B"]
                if set(choose) != names or set(evaluate) != names:
                    raise ValueError("confirmation candidate inventory is incomplete")
                candidates = [n for n, v in choose.items()
                              if isinstance(v, (int, float)) and not isinstance(v, bool)
                              and math.isfinite(v) and v >= 0]
                selected = min(candidates, key=lambda n: (choose[n], n)) if candidates else None
                net = evaluate[selected] if selected is not None else None
                template, base = evaluate["template+R"], evaluate[constant]
                valid = selected is not None and all(_positive(v) for v in (net, template, base))
                rows.append({"part": part["slug"], "band": part["band"],
                             "pick": selected, "constant": constant,
                             "refused": not valid,
                             "net_vs_template": math.log(net) - math.log(template) if valid else None,
                             "net_vs_constant": math.log(net) - math.log(base) if valid else None,
                             "joint_win": bool(valid and net < template and net < base)})
            bands = sorted({r["band"] for r in rows})
            joint = statistics.mean(sum(r["joint_win"] for r in rows if r["band"] == b)
                                    / sum(r["band"] == b for r in rows) for b in bands)
            template = _band_summary(rows, "net_vs_template")
            paired = _band_summary(rows, "net_vs_constant")
            refusals = sum(r["refused"] for r in rows)
            gates = {
                "complete_required_comparisons": refusals == 0,
                "template_margin": bool(template and template["band_median_log_ratio"] <= math.log(0.9)),
                "constant_margin": bool(paired and paired["band_median_log_ratio"] <= math.log(0.95)),
                "constant_sign_flip": bool(paired and paired["sign_flip_p_two_sided"] < 0.1),
                "joint_win_share": joint > 0.5,
            }
            output[f"{bs}|{amp}"] = {"rows": rows, "parts": len(rows), "bands": len(bands),
                                     "refusals": refusals, "joint_win_share": joint,
                                     "net_vs_template": template, "net_vs_constant": paired,
                                     "numeric_summaries_descriptive_only": refusals > 0,
                                     "gates": gates, "passed": all(gates.values())}
    return output


def combined_verdict(waveform, onset, amps):
    """Neither lag analysis alone can confirm an amp; both band sets must pass."""
    result = {}
    for amp in amps:
        keys = [f"{bs}|{amp}" for bs in BAND_SETS]
        primary = all(waveform[k]["passed"] for k in keys)
        sensitivity = all(onset[k]["passed"] for k in keys)
        result[amp] = {"waveform_passed": primary, "onset_passed": sensitivity,
                       "verdict_changed": primary != sensitivity,
                       "confirmed_amp_track_only": primary and sensitivity}
    return result


def _asset(path):
    path = pathlib.Path(path).expanduser().resolve()
    return {"path": str(path), "sha256": sha256(path)}


def prepare(*, model=MODEL, out=OUTPUT, distances=DEVELOPMENT / "distances.json",
            amps=("sw50r", "pr12")):
    from learn import set3

    menus = menu_hashes(amps)
    dev = set3.slugs("development")
    return {
        "version": 1, "split": "held_out", "approved": False,
        "amps": list(amps), "slugs": sorted(set3.slugs("held_out")),
        "out": str(pathlib.Path(out).expanduser().resolve()),
        "assets": {"model": _asset(model), "average": _asset(AVERAGE),
                   "validation": _asset(set3.DECLARATION), "plan": _asset(PLAN),
                   "development_distances": _asset(distances)},
        "code": {p: sha256(ROOT / p) for p in source_inventory()},
        "runtime": runtime_provenance(),
        "menus": menus,
        "constants": select_constants(json.loads(pathlib.Path(distances).read_text()), dev, menus),
    }


def _require_committed(path):
    path = pathlib.Path(path).resolve()
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("declaration and manifest must be inside the repository") from exc
    result = subprocess.run(["git", "show", f"HEAD:{relative.as_posix()}"], cwd=ROOT,
                            capture_output=True, check=False)
    if result.returncode or result.stdout != path.read_bytes():
        raise ValueError(f"input is not committed at HEAD: {relative}")


def validate_manifest(manifest_path, *, model, amps, parts, out, require_declared=True):
    """Fail before any held-out audio is opened if the frozen inputs changed."""
    from learn import set3

    path = pathlib.Path(manifest_path)
    manifest = json.loads(path.read_text())
    if manifest.get("version") != 1 or manifest.get("split") != "held_out":
        raise ValueError("not a set-3 confirmation manifest")
    if require_declared:
        if manifest.get("approved") is not True:
            raise ValueError("held-out confirmation still awaits user approval")
        _require_committed(path)
        _require_committed(PLAN)
        declared = PLAN.read_text().split("**declared:**", 1)
        if (len(declared) != 2 or not declared[1].strip()
                or declared[1].lstrip().startswith("_") or "DRAFT" in PLAN.read_text().splitlines()[0]):
            raise ValueError("held-out plan has not been declared")
    slugs = list(parts) if isinstance(parts, dict) else [p["slug"] for p in parts]
    if sorted(slugs) != sorted(set3.slugs("held_out")) or sorted(slugs) != manifest["slugs"]:
        raise ValueError("held-out part list changed")
    if list(amps) != manifest["amps"]:
        raise ValueError("confirmation amp list changed")
    output = pathlib.Path(out).expanduser().resolve()
    if output == DEVELOPMENT.resolve() or str(output) != manifest["out"]:
        raise ValueError("confirmation output differs from the frozen separate directory")
    expected = {"model": pathlib.Path(model).expanduser().resolve(), "average": AVERAGE.resolve(),
                "validation": set3.DECLARATION.resolve(), "plan": PLAN.resolve()}
    for key, wanted in expected.items():
        if pathlib.Path(manifest["assets"][key]["path"]).resolve() != wanted:
            raise ValueError(f"confirmation asset path changed: {key}")
    for key, asset in manifest["assets"].items():
        if sha256(asset["path"]) != asset["sha256"]:
            raise ValueError(f"confirmation asset changed: {key}")
    if set(manifest["code"]) != set(source_inventory()):
        raise ValueError("confirmation code inventory changed")
    for relative, digest in manifest["code"].items():
        if sha256(ROOT / relative) != digest:
            raise ValueError(f"confirmation code changed: {relative}")
        if require_declared:
            _require_committed(ROOT / relative)
    if runtime_provenance() != manifest["runtime"]:
        raise ValueError("confirmation runtime, renderer or installed Audio Unit changed")
    if menu_hashes(amps) != manifest["menus"]:
        raise ValueError("confirmation preset settings changed")
    constants = select_constants(
        json.loads(pathlib.Path(manifest["assets"]["development_distances"]["path"]).read_text()),
        set3.slugs("development"), manifest["menus"])
    if constants != manifest["constants"]:
        raise ValueError("confirmation constants do not follow the frozen development rule")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cmd", choices=("prepare",))
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.manifest.exists():
        parser.error("refusing to overwrite an existing manifest")
    args.manifest.write_text(json.dumps(prepare(), indent=2, allow_nan=False) + "\n")
    print(f"Prepared {args.manifest}; approval is false, held-out execution remains blocked.")


if __name__ == "__main__":
    main()
