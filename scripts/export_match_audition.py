#!/usr/bin/env python3
"""Export a completed match as a blind, level-matched R–A–B audition.

The reference must be a render of the exact probe performance (`paired_di` or
`probe`) unless --allow-unpaired is explicit. The output montage stays blind; a
separate key carries the run/candidate identity used by log_blind_verdict.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import secrets
import shlex
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, positive_float, positive_int, renderer_paths
from build_rab_audition import _finite_float, _nonnegative_float, _nonpositive_float


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_object(path: pathlib.Path, label: str):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"the run has no {label} at {path}")
    if not isinstance(value, dict):
        die(f"the {label} at {path} must be a JSON object")
    return value


def _recorded_file(value, run_dir: pathlib.Path, label: str) -> pathlib.Path:
    """Resolve old relative records only when exactly one location is plausible."""
    path = pathlib.Path(str(value or "")).expanduser()
    if path.is_absolute():
        if path.is_file():
            return path
        die(f"the recorded {label} does not exist at {path}")
    candidates = []
    for candidate in (PLUGIN_ROOT / path, run_dir / path):
        resolved = candidate.resolve()
        if resolved.is_file() and resolved not in candidates:
            candidates.append(resolved)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        die(f"the recorded relative {label} {path} cannot be found from the project "
            "root or run directory")
    die(f"the recorded relative {label} {path} is ambiguous: "
        + ", ".join(str(candidate) for candidate in candidates))


def _candidate_values(seed, spec):
    values = dict(seed)
    parameters = spec.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        die("the candidate spec has no parameters")
    for item in parameters:
        if not isinstance(item, dict):
            die("every candidate parameter must be an object")
        module, key = item.get("module"), item.get("key")
        if not isinstance(module, str) or not isinstance(key, str) or not key:
            die("a candidate parameter has no module/key path")
        if "value" not in item:
            die(f"candidate parameter {module}/{key} has no value")
        values[(module, key)] = item["value"]
    return values


def _settings(space, values, supported):
    result = {}
    for dimension in space.active(values):
        value = values.get((dimension.module, dimension.key))
        if value is None:
            continue
        if supported is not None and dimension.path not in supported:
            continue
        result[dimension.path] = value
    return result


def _run_record(run_dir: pathlib.Path, run_id: str):
    from match.store import STORE_NAME, Store

    store_path = run_dir / STORE_NAME
    if not store_path.is_file():
        die(f"the run has no render store at {store_path}")
    with Store(str(store_path)) as store:
        found = [run for run in store.runs() if run.run_id == run_id]
        di_hashes = {
            trial.di_sha for trial in store.trials(run_id)
            if trial.di_sha and abs(float(trial.di_offset_db or 0.0)) < 1e-12
        }
    if len(found) != 1:
        die(f"the store contains {len(found)} rows for run_id {run_id!r}, expected 1")
    return found[0], di_hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=positive_int)
    parser.add_argument("--probe-di", required=True, type=pathlib.Path,
                        help="the exact DI performance used by the match")
    parser.add_argument("--out-dir", type=pathlib.Path,
                        help="default: RUN_DIR/audition-candidate-N")
    parser.add_argument("--renderer", choices=("synthetic", "swift"),
                        help="default: the renderer recorded by summary.json")
    parser.add_argument("--duration", type=positive_float)
    parser.add_argument("--target-lufs", type=_finite_float, default=-20.0)
    parser.add_argument("--peak-ceiling-dbtp", type=_nonpositive_float, default=-1.0)
    parser.add_argument("--gap", type=_nonnegative_float, default=0.5)
    parser.add_argument("--cycle-gap", type=_nonnegative_float, default=1.0)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--mono", action="store_true")
    parser.add_argument("--allow-unpaired", action="store_true",
                        help="allow different reference/probe performances; the key "
                             "records that direct timing/content comparison is weak")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    summary = _read_object(run_dir / "summary.json", "summary")
    if summary.get("schema") != "tone-match-summary-v1":
        die(f"unsupported summary schema {summary.get('schema')!r}")
    shortlist = summary.get("shortlist")
    if not isinstance(shortlist, list) or not 1 <= args.candidate <= len(shortlist):
        die(f"candidate {args.candidate} is not in this run")
    candidate = shortlist[args.candidate - 1]
    if candidate.get("rank") != args.candidate:
        die(f"shortlist entry {args.candidate} has the wrong rank")

    reference = summary.get("reference") or {}
    regime = reference.get("regime")
    if regime not in ("paired_di", "probe") and not args.allow_unpaired:
        die(f"reference regime {regime!r} is not the exact probe performance.\n"
            "  Use a paired_di/probe run for blind R–A–B listening, or pass "
            "--allow-unpaired and treat timing/content differences as a limitation.")
    reference_path = _recorded_file(reference.get("path"), run_dir, "reference")
    recorded_reference_sha = ((reference.get("fingerprint") or {}).get("source")
                              or {}).get("sha256")
    if not recorded_reference_sha or _sha256(reference_path) != recorded_reference_sha:
        die("the recorded reference file no longer matches summary.json; refusing "
            "to audition different audio under the old measurement")
    probe_path = args.probe_di.expanduser()
    if not probe_path.is_file():
        die(f"--probe-di does not exist at {probe_path}")
    excerpt = reference.get("excerpt") or {}
    excerpt_start = float(excerpt.get("start_s", 0.0))
    excerpt_duration = excerpt.get("duration_s")
    audition_duration = (args.duration if args.duration is not None else
                         (None if excerpt_duration is None
                          else float(excerpt_duration)))

    run, recorded_di_hashes = _run_record(
        run_dir, str(summary.get("run_id", "")))
    if not run.template:
        die("the run store does not record its template path")
    template_path = _recorded_file(run.template, run_dir, "template")

    renderer_name = args.renderer or str((summary.get("renderer") or {}).get(
        "renderer_id", ""))
    if renderer_name not in ("synthetic", "swift"):
        die(f"cannot recreate recorded renderer {renderer_name!r}; pass --renderer")
    pack_id = str(summary.get("pack", ""))

    from analysis import io
    from match import space as space_module
    from scripts.build_rab_audition import build, _write_audio, _write_text
    from scripts.match_preset import _renderer, _seed_from_template

    space = space_module.build(pack_id)
    seed, _ = _seed_from_template(template_path, space, pack_id)
    spec = _read_object(run_dir / f"match-{args.candidate}.json", "candidate spec")
    candidate_values = _candidate_values(seed, spec)

    renderer = _renderer(renderer_name, pack_id)
    try:
        metadata = renderer.metadata()
        recorded = summary.get("renderer") or {}
        if (metadata.renderer_id != recorded.get("renderer_id")
                or metadata.plugin_version != recorded.get("plugin_version")
                or metadata.renderer_build != recorded.get("renderer_build")):
            die("the available renderer/plugin build does not match the completed "
                "run; rerun the match before collecting a listening verdict")
        probe = io.load(str(probe_path), target_rate=metadata.sample_rate)
        from match.renderer import _hash_audio
        probe_audio_sha = _hash_audio(probe.samples)
        if probe_audio_sha not in recorded_di_hashes:
            die("--probe-di does not match any reference-level DI recorded in the "
                "run store; pass the exact performance used by match_preset.py")
        supported = renderer_paths(renderer)
        template_render = renderer.render(
            probe.samples, _settings(space, seed, supported)).audio
        candidate_render = renderer.render(
            probe.samples, _settings(space, candidate_values, supported)).audio
    finally:
        close = getattr(renderer, "close", None)
        if close is not None:
            close()

    out_dir = (args.out_dir or
               run_dir / f"audition-candidate-{args.candidate}").expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    template_wav = raw_dir / "template.wav"
    candidate_wav = raw_dir / f"candidate-{args.candidate}.wav"
    montage_path = out_dir / "audition.flac"
    key_path = out_dir / "audition.flac.key.json"
    for path in (template_wav, candidate_wav, montage_path, key_path):
        if path.exists() and not args.force:
            die(f"{path} already exists; choose another --out-dir or pass --force")

    _write_audio(template_wav, template_render, metadata.sample_rate)
    _write_audio(candidate_wav, candidate_render, metadata.sample_rate)
    blind_seed = args.seed if args.seed is not None else secrets.randbits(64)
    montage, key = build(
        reference=reference_path,
        first=template_wav,
        second=candidate_wav,
        starts=(excerpt_start, excerpt_start, excerpt_start),
        duration_s=audition_duration,
        target_lufs=args.target_lufs,
        peak_ceiling_dbtp=args.peak_ceiling_dbtp,
        gap_s=args.gap,
        cycle_gap_s=args.cycle_gap,
        seed=blind_seed,
        force_mono=args.mono,
    )
    _write_audio(montage_path, montage, key["sample_rate"])
    key["output"] = {
        "path": str(montage_path),
        "sha256": _sha256(montage_path),
        "format": "flac",
    }
    key["match"] = {
        "schema": "match-audition-1",
        "run_dir": str(run_dir),
        "run_id": summary["run_id"],
        "pack": pack_id,
        "candidate_rank": args.candidate,
        "roles": {"first": "template", "second": "candidate"},
        "reference_regime": regime,
        "allow_unpaired": bool(args.allow_unpaired),
        "probe_di": {"path": str(probe_path.resolve()),
                     "sha256": _sha256(probe_path),
                     "audio_sha256": probe_audio_sha},
        "renderer": metadata.as_dict(),
    }
    key["invocation"] = [sys.executable, str(pathlib.Path(__file__)), *sys.argv[1:]]
    if args.seed is None:
        key["invocation"].extend(["--seed", str(blind_seed)])
    _write_text(key_path, json.dumps(key, indent=2) + "\n")

    print(f"wrote blind audition: {montage_path}")
    print(f"private key: {key_path}")
    print("listen without opening the key: Reference -> A -> B, repeated once")
    print("then record closeness with:")
    print("  python scripts/log_blind_verdict.py \\")
    print(f"    --key {shlex.quote(str(key_path))} --choice A-or-B \\")
    print("    --listener YOUR_NAME")


if __name__ == "__main__":
    guarded(main)
