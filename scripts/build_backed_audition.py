"""Make a blind, shared-backing audition and score the *bare* guitar.

    python scripts/build_backed_audition.py --manifest private.json --out-dir runs/audition

The manifest fixes crops and mix balance before listening. Output is a short
Reference–A–B FLAC plus a separate private key with frozen objective scores.
This never renders a plugin; AC20 and Tone King inputs need exact fresh-process
render proof.
Audio inputs must be WAV, FLAC, AIFF or Ogg; convert an MP3 reference to a
private WAV first and bind that converted file's hash in the manifest.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import secrets
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(pathlib.Path(__file__).resolve().parent)]

from _cli import guarded
from build_rab_audition import (_audition_channels, _slice, _static_gain_to_lufs,
                                _write_audio, _write_text)


def _number(value, name: str, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite number") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return number


def _source(spec: dict, role: str):
    from analysis import io
    from analysis.listening import sha256

    if not isinstance(spec, dict):
        raise ValueError(f"{role} must be an object")
    path = pathlib.Path(spec["path"]).expanduser().resolve()
    if not path.is_file() or sha256(path) != spec.get("sha256"):
        raise ValueError(f"{role} is missing or its SHA-256 changed: {path}")
    return path, io.load(path)


def _crop(audio, spec: dict, role: str, duration: float):
    start = _number(spec.get("start_s"), f"{role}.start_s", 0)
    if start + duration > audio.duration_s + 1 / audio.sample_rate:
        raise ValueError(f"{role} has less than {duration:g} s after {start:g} s")
    clip = _slice(audio, start, duration)
    if clip.frames != round(duration * audio.sample_rate):
        raise ValueError(f"{role} crop is shorter than requested")
    return clip


def _provenance(spec: dict, path: pathlib.Path):
    from analysis.listening import sha256, verified_fresh_render

    model = spec.get("amp_model")
    pack_id = spec.get("pack", "morgan")
    allowed = {"morgan": ("AC20", "PR12", "SW50R"),
               "toneking": ("Rhythm Channel", "Lead Channel")}
    if model == "non-Morgan" and "pack" not in spec:
        pack_id = "unknown"  # Preserve older, explicitly unverified inputs.
    elif pack_id not in allowed or model not in allowed[pack_id]:
        raise ValueError("each alternative needs an amp_model valid for its pack")
    record = spec.get("render_record")
    if record is None:
        if model == "AC20" or pack_id == "toneking":
            raise ValueError(f"{model} requires a fresh-process record for this exact audio")
        return {"pack": pack_id, "amp_model": model, "process_policy": "unknown"}
    if pack_id == "unknown":
        raise ValueError("an unknown pack cannot have a verified fresh-process record")
    record_path = pathlib.Path(record).expanduser().resolve()
    if not record_path.is_file():
        raise ValueError(f"missing render record: {record_path}")
    source = {"pack": pack_id, "amp_model": model, "process_policy": "fresh",
              "render_record": {"path": str(record_path), "sha256": sha256(record_path)}}
    if not verified_fresh_render(source, {"path": str(path), "sha256": sha256(path)}):
        raise ValueError("render record does not bind this fresh-process audio")
    return source


def build(manifest: dict, *, seed: int):
    """Compute the montage and private evidence before anything is written."""
    import numpy as np
    from analysis import io
    from analysis.listening import score_record

    if manifest.get("schema") != "prospective-backed-listening-v1":
        raise ValueError("expected prospective-backed-listening-v1 manifest")
    if not manifest.get("id") or not manifest.get("target_id"):
        raise ValueError("manifest needs id and independent-song target_id")
    purpose = manifest.get("purpose", "prospective")
    if purpose not in ("prospective", "workflow-rehearsal"):
        raise ValueError("purpose must be prospective or workflow-rehearsal")
    if purpose == "workflow-rehearsal" and manifest["target_id"] != "unassigned":
        raise ValueError("a workflow rehearsal must use target_id=unassigned")
    reference, backing = manifest["reference"], manifest["backing"]
    alternatives = manifest["alternatives"]
    if not all(isinstance(value, dict) for value in (reference, backing, alternatives)):
        raise ValueError("reference, backing and alternatives must be objects")
    if set(alternatives) != {"first", "second"}:
        raise ValueError("alternatives must be exactly first and second")
    if backing.get("guitar_removed") is not True:
        raise ValueError("backing must explicitly declare guitar_removed=true; "
                         "do not use the intact original as backing")
    if backing.get("sha256") == reference.get("sha256"):
        raise ValueError("backing and reference are the same file; backing must remove guitar")
    if reference.get("regime") not in (
            "probe", "paired_di", "isolated_stem", "separated_stem", "mix"):
        raise ValueError("reference needs an explicit known regime")
    duration = _number(reference.get("duration_s"), "reference.duration_s", .4)
    mix = manifest["mix"]
    if not isinstance(mix, dict):
        raise ValueError("mix must be an object")
    guitar_target = _number(mix.get("guitar_target_lufs"), "mix.guitar_target_lufs")
    master_target = _number(mix.get("master_target_lufs"), "mix.master_target_lufs")
    backing_gain = _number(backing.get("gain_db"), "backing.gain_db")
    ceiling = _number(mix.get("peak_ceiling_dbtp"), "mix.peak_ceiling_dbtp")
    max_delta = _number(mix.get("max_ab_lufs_delta", .5), "mix.max_ab_lufs_delta", 0)
    gap_s = _number(mix.get("gap_s", .5), "mix.gap_s", 0)
    cycles = mix.get("cycles", 1)
    if ceiling > 0 or type(cycles) is not int or cycles not in (1, 2):
        raise ValueError("peak ceiling must be nonpositive and cycles must be 1 or 2")

    roles = ("reference", "backing", "first", "second")
    specs = (reference, backing, alternatives["first"], alternatives["second"])
    paths, loaded = zip(*(_source(spec, role) for spec, role in zip(specs, roles)))
    provenances = {role: _provenance(spec, path)
                   for role, spec, path in zip(roles[2:], specs[2:], paths[2:])}
    audible, channels = _audition_channels(loaded, force_mono=False)
    clips = [_crop(audio, spec, role, duration)
             for audio, spec, role in zip(audible, specs, roles)]
    levels = [io.loudness_lufs(clip) for clip in (clips[0], clips[2], clips[3])]
    if any(value is None for value in levels):
        raise ValueError("reference and both guitars need measurable loudness")
    guitar_gains, guitars = [], []
    for clip, before in zip(clips[2:], levels[1:]):
        gain, matched, _ = _static_gain_to_lufs(clip, guitar_target, before)
        guitar_gains.append(gain)
        guitars.append(matched.samples.astype(np.float64))
    bed = clips[1].samples.astype(np.float64) * 10 ** (backing_gain / 20)
    reference_samples = clips[0].samples.astype(np.float64)
    mixes = [bed + guitar for guitar in guitars]
    mix_levels = [io.loudness_lufs(io.from_samples(samples)) for samples in mixes]
    if any(value is None for value in mix_levels):
        raise ValueError("backed alternatives need measurable loudness")
    difference = abs(mix_levels[0] - mix_levels[1])
    if difference > max_delta:
        raise ValueError(f"A/B mixes differ by {difference:.3f} LU; limit is "
                         f"{max_delta:.3f} LU. Do not audition a loudness-confounded pair.")
    peaks = [io.true_peak_dbtp(io.from_samples(samples))
             for samples in (reference_samples, *mixes)]
    if any(value is None for value in peaks):
        raise ValueError("cannot verify the true peak of every audition segment")
    master_gain = min(master_target - levels[0], ceiling - max(peaks))
    scale = 10 ** (master_gain / 20)

    # One backing crop and one master scalar for both alternatives. Only their
    # independently level-matched guitar signals differ.
    swap = bool(random.Random(seed).getrandbits(1))
    blind = {"A": "second" if swap else "first", "B": "first" if swap else "second"}
    segment = {"Reference": reference_samples * scale,
               "A": mixes[1 if swap else 0] * scale,
               "B": mixes[0 if swap else 1] * scale}
    silence = np.zeros((round(gap_s * io.SAMPLE_RATE), channels))
    pieces, timeline, cursor = [], [], 0
    for index, label in enumerate(("Reference", "A", "B") * cycles):
        if index:
            pieces.append(silence)
            cursor += len(silence)
        pieces.append(segment[label])
        timeline.append({"label": label, "start_s": cursor / io.SAMPLE_RATE,
                         "end_s": (cursor + len(segment[label])) / io.SAMPLE_RATE})
        cursor += len(segment[label])
    montage = np.concatenate(pieces).astype(np.float32)

    def score_spec(spec, path, gain):
        return {"path": str(path), "sha256": spec["sha256"],
                "start_s": spec["start_s"], "duration_s": duration,
                "gain_db": gain, "promote_stereo": channels == 2}

    bare = {role: score_spec(spec, path, gain + master_gain)
            for role, spec, path, gain in zip(roles[2:], specs[2:], paths[2:], guitar_gains)}
    scored = score_record({
        "id": manifest["id"], "target_id": manifest["target_id"],
        "reference": {**score_spec(reference, paths[0], master_gain),
                      "regime": reference["regime"]},
        "alternatives": {label: bare[role] for label, role in blind.items()},
        "render_provenance": {label: provenances[role] for label, role in blind.items()},
        "listening_context": "Listener hears common backing; objective scores bare guitar "
                             "against the reference. Primary distance excludes level.",
    })
    evidence = {
        "schema": "prospective-backed-audition-v1", "seed": seed,
        "purpose": purpose, "limitations": manifest.get("limitations", []),
        "blind_key": blind, "sample_rate": io.SAMPLE_RATE, "channels": channels,
        "duration_s": duration, "timeline": timeline,
        "source_paths": dict(zip(roles, map(str, paths))),
        "source_sha256": {role: spec["sha256"] for role, spec in zip(roles, specs)},
        "guitar_target_lufs": guitar_target,
        "guitar_static_gain_db": dict(zip(roles[2:], guitar_gains)),
        "backing_gain_db": backing_gain, "common_master_gain_db": master_gain,
        "backed_lufs_before_master": dict(zip(roles[2:], mix_levels)),
        "reference_lufs_before_master": levels[0], "ab_lufs_delta": difference,
        "peak_ceiling_dbtp": ceiling,
        "backing_policy": "same backing crop, gain and master scalar in A and B; "
                          "guitar_removed is declared, not proven, and leakage remains possible",
        "objective_record": scored,
    }
    return montage, evidence


def main() -> None:
    from analysis import io
    from analysis.listening import sha256
    from score_listening import _require_private_out_dir

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    parser.add_argument("--seed", type=int, help="blind seed, generated if omitted")
    args = parser.parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    _require_private_out_dir(manifest_path.parent)
    manifest = json.loads(manifest_path.read_text())
    out = _require_private_out_dir(args.out_dir)
    if out.exists() or out.is_symlink():
        raise ValueError("choose a new private output directory; auditions are immutable")
    seed = args.seed if args.seed is not None else secrets.randbits(64)
    montage, evidence = build(manifest, seed=seed)
    evidence["manifest"] = {"path": str(manifest_path), "sha256": sha256(manifest_path)}
    audio_path = out / "audition.flac"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Do not claim the immutable destination until the written audio and key
    # have both passed verification. The staging directory is on the same
    # filesystem, so publication is one directory rename.
    with tempfile.TemporaryDirectory(prefix=f".{out.name}-", dir=out.parent) as temporary:
        staged = pathlib.Path(temporary)
        _require_private_out_dir(staged)
        staged_audio = staged / "audition.flac"
        _write_audio(staged_audio, montage, evidence["sample_rate"])
        decoded = io.load(staged_audio)
        if decoded.frames != len(montage) or decoded.channels != evidence["channels"]:
            raise ValueError("written audition changed its duration or channel count")
        peak = io.true_peak_dbtp(decoded)
        if peak is None or peak > evidence["peak_ceiling_dbtp"] + .02:
            raise ValueError("written audition exceeds its true-peak ceiling")
        evidence["output"] = {"path": str(audio_path), "sha256": sha256(staged_audio),
                              "true_peak_dbtp": peak}
        _write_text(staged / "private-key.json",
                    json.dumps(evidence, indent=2, allow_nan=False) + "\n")
        if out.exists() or out.is_symlink():
            raise ValueError("choose a new private output directory; auditions are immutable")
        os.rename(staged, out)
    print(f"wrote {audio_path} (Reference–A–B; key kept separately)")
    print("record closeness and preference before opening private-key.json")


if __name__ == "__main__":
    guarded(main)
