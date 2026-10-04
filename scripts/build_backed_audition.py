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
from _listening_trials import plan_trials


# Crops cut by the first rule or by crop rule 2 (docs/validation-datasets.md).
CROP_SCHEMAS = ("validation-crops-1", "validation-crops-2")

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
        raise ValueError(f"{role} is too short for the requested crop: "
                         f"has less than {duration:g} s after {start:g} s")
    clip = _slice(audio, start, duration)
    if clip.frames != round(duration * audio.sample_rate):
        raise ValueError(f"{role} crop is too short")
    return clip


def _unmeasurable_loudness(clip) -> str:
    """Explain a missing loudness without treating faint audio as silence."""
    import numpy as np

    if not np.any(clip.samples):
        return "silent"
    if clip.duration_s < .4:
        return "too short for the 0.4 s loudness gate"
    return "non-silent but too quiet for the loudness gate"


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


def _validation_crop(manifest: dict, reference: dict, backing: dict,
                     alternatives: dict) -> dict | None:
    """Bind a crop-based audition to its mix, backing and exact fresh DI renders."""
    from analysis.listening import sha256

    named = manifest.get("validation_crop_record")
    if named is None:
        return None
    path = pathlib.Path(named).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"missing validation crop record: {path}")
    record = json.loads(path.read_text(encoding="utf-8"))
    outputs = record.get("outputs", {})
    if record.get("schema") not in CROP_SCHEMAS or not all(
            isinstance(outputs.get(role), dict) for role in ("di", "mix", "backing")):
        raise ValueError("invalid validation crop record")

    def matches(spec: dict, role: str) -> bool:
        output = outputs[role]
        return (pathlib.Path(spec.get("path", "")).expanduser().resolve() ==
                pathlib.Path(output.get("path", "")).expanduser().resolve()
                and spec.get("sha256") == output.get("sha256")
                and sha256(output["path"]) == output["sha256"])

    # The crop's mix and backing, or both without the singing — never one of each,
    # or the singing alone would tell the reference from A and B.
    pairs = [("mix", "backing"), ("mix_instrumental", "backing_instrumental")]
    played = next((pair for pair in pairs
                   if all(isinstance(outputs.get(role), dict) for role in pair)
                   and matches(reference, pair[0]) and matches(backing, pair[1])), None)
    if (played is None
            or reference.get("regime") != "mix"
            or float(reference.get("start_s", -1)) != 0
            or float(reference.get("duration_s", -1)) != record.get("excerpt_duration_s")
            or float(backing.get("start_s", -1)) != 0
            or float(backing.get("gain_db", float("nan"))) != 0):
        raise ValueError("validation audition must use the crop's whole mix and unchanged backing")
    di = outputs["di"]
    if sha256(di["path"]) != di["sha256"]:
        raise ValueError("validation DI crop hash changed")
    for label, spec in alternatives.items():
        if not spec.get("render_record"):
            raise ValueError(f"{label} needs a fresh-process render record from the crop DI")
    audio_paths = {pathlib.Path(spec["path"]).expanduser().resolve()
                   for spec in alternatives.values()}
    proof_paths = {pathlib.Path(spec["render_record"]).expanduser().resolve()
                   for spec in alternatives.values() if spec.get("render_record")}
    if len(audio_paths) != 2 or len(proof_paths) != 2:
        raise ValueError("validation alternatives need two distinct fresh renders")
    for label, spec in alternatives.items():
        proof_path = pathlib.Path(spec["render_record"]).expanduser().resolve()
        if not proof_path.is_file():
            raise ValueError(f"missing {label} fresh-process render record")
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        source_di = proof.get("di", {})
        if (proof.get("process_policy") != "fresh"
                or pathlib.Path(source_di.get("path", "")).expanduser().resolve() !=
                pathlib.Path(di["path"]).expanduser().resolve()
                or source_di.get("sha256") != di["sha256"]):
            raise ValueError(f"{label} was not freshly rendered from this crop DI")
    declaration = record.get("declaration")
    if record.get("split") == "held_out":
        if (not isinstance(declaration, dict)
                or manifest.get("declared_test_id") != declaration.get("test_id")):
            raise ValueError("held-out audition must name the crop's declared_test_id")
    return {"path": str(path), "sha256": sha256(path),
            "split": record.get("split"), "declaration": declaration,
            "reference_output": played[0], "backing_output": played[1]}


def _require_crop_binding(manifest: dict, reference: dict, backing: dict) -> None:
    """Do not silently treat crop WAVs as generic unverified mix inputs."""
    named = manifest.get("validation_crop_record")
    mode = manifest.get("validation_mode")
    if mode not in (None, "declared"):
        raise ValueError("validation_mode must be declared when present")
    if mode == "declared" and named is None:
        raise ValueError("declared validation mode needs validation_crop_record")
    if named is not None and mode != "declared":
        raise ValueError("validation_crop_record needs validation_mode=declared")
    for spec in (reference, backing):
        source = pathlib.Path(spec.get("path", "")).expanduser().resolve()
        candidate = source.parent / "record.json"
        if not candidate.is_file():
            continue
        try:
            record = json.loads(candidate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue  # An unrelated generic-audition directory may have a record.json.
        if not isinstance(record, dict) or record.get("schema") not in CROP_SCHEMAS:
            continue
        outputs = record.get("outputs")
        if (isinstance(outputs, dict)
                and any(source == pathlib.Path(item.get("path", "")).expanduser().resolve()
                        for item in outputs.values() if isinstance(item, dict))
                and (named is None or pathlib.Path(named).expanduser().resolve() != candidate)):
            raise ValueError("validation crop audio needs its exact validation_crop_record")


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
    _require_crop_binding(manifest, reference, backing)
    crop_binding = _validation_crop(manifest, reference, backing, alternatives)
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
    reliability = manifest.get("reliability", {})
    if not isinstance(reliability, dict) or set(reliability) - {"hidden_repeats", "catch_trial"}:
        raise ValueError("reliability must contain only hidden_repeats and catch_trial")
    hidden_repeats = reliability.get("hidden_repeats", 0)
    catch_trial = reliability.get("catch_trial", False)

    roles = ("reference", "backing", "first", "second")
    specs = (reference, backing, alternatives["first"], alternatives["second"])
    paths, loaded = zip(*(_source(spec, role) for spec, role in zip(specs, roles)))
    provenances = {role: _provenance(spec, path)
                   for role, spec, path in zip(roles[2:], specs[2:], paths[2:])}
    audible, channels = _audition_channels(loaded, force_mono=False)
    clips = [_crop(audio, spec, role, duration)
             for audio, spec, role in zip(audible, specs, roles)]
    metered = (("reference", clips[0]), ("first", clips[2]), ("second", clips[3]))
    levels = [io.loudness_lufs(clip) for _, clip in metered]
    failed = [f"{role} is {_unmeasurable_loudness(clip)}"
              for (role, clip), value in zip(metered, levels) if value is None]
    if failed:
        raise ValueError("reference and both guitars need measurable loudness: "
                         + "; ".join(failed))
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
    trials = plan_trials(seed, blind, repeats=hidden_repeats, catch=catch_trial)
    segment = {"reference": reference_samples * scale,
               "first": mixes[0] * scale, "second": mixes[1] * scale}
    silence = np.zeros((round(gap_s * io.SAMPLE_RATE), channels))
    trial_gap = np.zeros((round(2.0 * io.SAMPLE_RATE), channels))
    pieces, timeline, cursor = [], [], 0
    trial_blocks = trials or [{"ordinal": 1, "blind_key": blind}]
    for trial_index, trial in enumerate(trial_blocks):
        if trial_index:
            pieces.append(trial_gap)
            cursor += len(trial_gap)
        labels = ("Reference", "A", "B") * cycles
        for index, label in enumerate(labels):
            if index:
                pieces.append(silence)
                cursor += len(silence)
            role = "reference" if label == "Reference" else trial["blind_key"][label]
            samples = segment[role]
            pieces.append(samples)
            row = {"label": label, "start_s": cursor / io.SAMPLE_RATE,
                   "end_s": (cursor + len(samples)) / io.SAMPLE_RATE}
            if trials is not None:
                row["trial"] = trial["ordinal"]
            timeline.append(row)
            cursor += len(samples)
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
    }, include_match_v3=True)
    evidence = {
        "schema": "prospective-backed-audition-v1", "seed": seed,
        "objective_profiles_frozen": scored["objective_profiles_frozen"],
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
    if crop_binding is not None:
        evidence["validation_mode"] = "declared"
        evidence["validation_crop_record"] = crop_binding
    if trials is not None:
        evidence["trials"] = trials
        evidence["trial_gap_s"] = 2.0
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
    if "trials" in evidence:
        print(f"listen to {len(evidence['trials'])} numbered blocks; record one closeness answer "
              "per block in order before opening private-key.json")
    else:
        print("record which alternative is closer before opening private-key.json")


if __name__ == "__main__":
    guarded(main)
