"""Audio-only loss-profile predictions, kept separate from listener judgments.

Input records explicitly name the bare guitar, target, processing and target group.
No backing removal, level correction, target inference, or preset penalty is invented.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from . import io
from .compare import PROFILE_PATH, Objectives, compare, load_profile, scalar
from .fingerprint import fingerprint


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_hashes():
    directory = Path(__file__).parent
    return {name: sha256(directory / name) for name in
            ("listening.py", "compare.py", "fingerprint.py", "features.py", "io.py", "loss_profiles.json")}


def verified_fresh_render(source: dict, audio_spec: dict) -> bool:
    """A declaration alone is not proof that the exact audio is fresh."""
    binding = source.get("render_record")
    if binding is None:
        return False
    if source.get("process_policy") != "fresh":
        raise ValueError("render provenance declaration conflicts with its fresh-process record")
    import json
    record_path = Path(binding["path"]).expanduser().resolve()
    if sha256(record_path) != binding.get("sha256"):
        raise ValueError("fresh render record hash changed")
    proof = json.loads(record_path.read_text())
    if (proof.get("schema") != "listening-fresh-render-v1" or
            proof.get("pack") != "morgan" or
            proof.get("amp_model") != source.get("amp_model") or
            proof.get("process_policy") != "fresh" or
            "process=fresh" not in proof.get("renderer", {}).get("quality_mode", "") or
            Path(proof.get("audio", {}).get("path", "")).expanduser().resolve() !=
            Path(audio_spec["path"]).expanduser().resolve() or
            proof.get("audio", {}).get("sha256") != audio_spec.get("sha256") or
            sha256(audio_spec["path"]) != audio_spec.get("sha256")):
        raise ValueError("fresh render record does not prove exact AC20 audio and renderer policy")
    return True


def verified_fresh_ac20(source: dict, audio_spec: dict) -> bool:
    return source.get("amp_model") == "AC20" and verified_fresh_render(source, audio_spec)


def _audio(spec):
    """Load exactly the declared source region, with explicit playback transforms."""
    path = Path(spec["path"]).expanduser().resolve()
    digest = sha256(path)
    if spec.get("sha256") != digest:
        raise ValueError(f"audio hash missing or changed: {path}")
    audio = io.load(path)
    start_s = float(spec.get("start_s", 0))
    duration_s = spec.get("duration_s")
    if duration_s is not None and (not math.isfinite(float(duration_s)) or float(duration_s) <= 0):
        raise ValueError("duration must be finite and positive")
    gain_db = float(spec.get("gain_db", 0))
    if not math.isfinite(start_s) or start_s < 0 or not math.isfinite(gain_db):
        raise ValueError("start and gain must be finite; start must be nonnegative")
    start = round(start_s * audio.sample_rate)
    frames = audio.frames - start if duration_s is None else round(float(duration_s) * audio.sample_rate)
    if frames < .4 * audio.sample_rate or start + frames > audio.frames:
        raise ValueError("audio region is too short or extends past the source")
    samples = audio.samples[start:start + frames]
    if spec.get("mono", False):
        samples = samples.mean(axis=1)
    elif spec.get("promote_stereo", False) and samples.shape[1] == 1:
        import numpy as np
        samples = np.repeat(samples, 2, axis=1)
    audio = io.from_samples(samples * 10 ** (gain_db / 20), audio.sample_rate)
    import numpy as np
    if not np.isfinite(audio.samples).all() or io.loudness_lufs(audio) is None:
        raise ValueError("audio region is non-finite or has no measurable loudness")
    return audio


def score_record(record: dict, cache: dict | None = None) -> dict:
    """Return a score sidecar; preserve the caller's verdict and source descriptors.

    Cache is process-local, content-addressed, and never substitutes for checking
    the files. Historical records without trustworthy sources remain unscored.
    """
    import json
    result = {key: value for key, value in record.items() if key not in ("objective_scoring", "agreement", "agreement_with_level", "scoring_error")}
    if set(record.get("alternatives", {})) != {"A", "B"}:
        raise ValueError("exactly two explicitly mapped alternatives A and B are required")
    if not record.get("target_id"):
        raise ValueError("an explicit target_id is required; repeats must share it")
    cache = {} if cache is None else cache
    profile = "unpaired-v1"
    profile_data = load_profile(profile)

    def printed(spec, regime):
        key = json.dumps({"source": spec, "regime": regime}, sort_keys=True)
        if key not in cache:
            cache[key] = fingerprint(_audio(spec), regime=regime, excerpt_s=None)
        elif sha256(Path(spec["path"]).expanduser()) != spec.get("sha256"):
            raise ValueError("cached audio hash changed")
        return cache[key]

    target = printed(record["reference"], record["reference"]["regime"])
    scores = {}
    for label, spec in record["alternatives"].items():
        fp = printed(spec, "probe")
        objectives = compare(target, fp, profile=profile)
        without_level = Objectives(values={key: value for key, value in objectives.values.items() if key != "level"}, profile=profile)
        distance = scalar(without_level)
        distance_with_level = scalar(objectives)
        if distance is None or not math.isfinite(distance):
            raise ValueError("no finite audio distance is measurable")
        measured = {key: value for key, value in objectives.values.items()
                    if key != "level" and value is not None and profile_data["weights"].get(key, 0) > 0}
        denominator = sum(profile_data["weights"][key] for key in measured)
        scores[label] = {"distance": distance, "distance_with_level": distance_with_level, "objectives": objectives.to_dict(),
                         "effective_weights": {key: profile_data["weights"][key] / denominator for key in measured},
                         "fingerprint": fp.to_dict()}
    score_a, score_b = (scores[label]["distance"] for label in ("A", "B"))
    prediction = "indistinguishable" if math.isclose(score_a, score_b, rel_tol=0, abs_tol=1e-9) else ("A" if score_a < score_b else "B")
    full_a, full_b = (scores[label]["distance_with_level"] for label in ("A", "B"))
    with_level_prediction = "indistinguishable" if math.isclose(full_a, full_b, rel_tol=0, abs_tol=1e-9) else ("A" if full_a < full_b else "B")
    term_coverage_equal = {
        dimension: set(scores["A"]["objectives"]["detail"].get(dimension, {})) ==
                   set(scores["B"]["objectives"]["detail"].get(dimension, {}))
        for dimension in (set(scores["A"]["objectives"]["detail"]) |
                          set(scores["B"]["objectives"]["detail"]))
    }
    coverage_equal = scores["A"]["effective_weights"] == scores["B"]["effective_weights"]
    comparable_coverage = coverage_equal and all(term_coverage_equal.values())
    result["objective_scoring"] = {
        "schema": "listening-objective-v1", "profile": profile,
        "scope": "audio-only; same profile and compare/scalar code as matching; not the full optimizer score",
        "primary_excluded_audio_terms": ["level"],
        "level_policy": "Primary distance excludes level and renormalizes remaining measured weights; standard audio score retained as distance_with_level. Listening deliberately removes loudness differences.",
        "unavailable_non_audio_terms": ["prior_deviation", "complexity"],
        "profile_sha256": sha256(PROFILE_PATH), "implementation_sha256": implementation_hashes(),
        "reference_fingerprint": target.to_dict(), "alternatives": scores,
        "prediction": prediction, "distance_B_minus_A": score_b - score_a,
        "prediction_with_level": with_level_prediction,
        "prediction_comparable": comparable_coverage,
        "level_changes_prediction": prediction != with_level_prediction,
        "tie_policy": "1e-9 numerical equality only; not a perceptual or backend-noise threshold",
        "coverage_equal": coverage_equal,
        "term_coverage_equal": term_coverage_equal,
    }
    provenance = record.get("render_provenance") or {}
    result["objective_scoring"]["amp_model_unknown"] = [
        label for label in ("A", "B")
        if provenance.get(label, {}).get("amp_model") not in ("AC20", "PR12", "SW50R", "non-Morgan")
    ]
    result["objective_scoring"]["ac20_history_uncertain"] = [
        label for label in ("A", "B")
        if provenance.get(label, {}).get("amp_model") == "AC20"
        and not verified_fresh_ac20(provenance[label], record["alternatives"][label])
    ]
    verdict = record.get("verdict") or {}
    result["agreement"] = {}
    result["agreement_with_level"] = {}
    for question in ("closer", "preferred"):
        answer = verdict.get(question)
        if answer not in (None, "A", "B", "indistinguishable"):
            raise ValueError(f"invalid {question} verdict: {answer!r}")
        if answer is None:
            status, agrees = "no_verdict", None
        elif not comparable_coverage:
            status, agrees = "unequal_coverage", None
        elif answer == "indistinguishable":
            status, agrees = "listener_tie", prediction == answer
        elif prediction == "indistinguishable":
            status, agrees = "objective_tie", False
        else:
            agrees = answer == prediction
            status = "agree" if agrees else "disagree"
        result["agreement"][question] = {"status": status, "agrees": agrees}
        if answer is None:
            status, agrees = "no_verdict", None
        elif not comparable_coverage:
            status, agrees = "unequal_coverage", None
        elif answer == "indistinguishable":
            status, agrees = "listener_tie", with_level_prediction == answer
        elif with_level_prediction == "indistinguishable":
            status, agrees = "objective_tie", False
        else:
            agrees = answer == with_level_prediction
            status = "agree" if agrees else "disagree"
        result["agreement_with_level"][question] = {"status": status, "agrees": agrees}
    return result


def agreement_report(records: list[dict]) -> dict:
    """One equal-weight descriptive summary per target, never an n of trials."""
    groups: dict[str, dict[str, Any]] = {}
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate comparison ids")
    for record in records:
        target = record["target_id"]
        if target == "unassigned":
            continue
        group = groups.setdefault(target, {"comparisons": [], "closer": {}, "preferred": {}})
        group["comparisons"].append(record["id"])
        uncertain = bool(record.get("objective_scoring", {}).get("ac20_history_uncertain"))
        unknown = bool(record.get("objective_scoring", {}).get("amp_model_unknown"))
        group["ac20_history_uncertain_count_not_independent_n"] = (
            group.get("ac20_history_uncertain_count_not_independent_n", 0) + int(uncertain))
        group["amp_model_unknown_count_not_independent_n"] = (
            group.get("amp_model_unknown_count_not_independent_n", 0) + int(unknown))
        for question in ("closer", "preferred"):
            scoring = record.get("objective_scoring", {})
            unequal = (scoring.get("coverage_equal") is False or
                       scoring.get("prediction_comparable") is False or
                       any(value is False for value in scoring.get("term_coverage_equal", {}).values()))
            if "scoring_error" in record:
                status = "unscored"
            elif unequal:
                status = "unequal_coverage"
            else:
                status = record.get("agreement", {}).get(question, {}).get("status", "unscored")
            counts = group[question].setdefault("diagnostic_counts_not_independent_n", {})
            counts[status] = counts.get(status, 0) + 1
    for group in groups.values():
        for question in ("closer", "preferred"):
            row = group[question]
            counts = row["diagnostic_counts_not_independent_n"]
            decisive = counts.get("agree", 0) + counts.get("disagree", 0)
            row["decisive_agreement_fraction"] = None if not decisive else counts.get("agree", 0) / decisive
    summary = {}
    for question in ("closer", "preferred"):
        fractions = [group[question]["decisive_agreement_fraction"] for group in groups.values()
                     if group[question]["decisive_agreement_fraction"] is not None]
        summary[question] = {"target_groups_with_decisive_verdicts": len(fractions),
                             "equal_target_weighted_agreement": None if not fractions else sum(fractions) / len(fractions)}
    return {"schema": "listening-agreement-v1", "target_groups": groups, "summary": summary,
            "ungrouped_comparisons": [r["id"] for r in records if r["target_id"] == "unassigned"],
            "interpretation": "Descriptive audit only. Repeats and backed revisits share their target's single weight. Target independence must be justified externally; shared songs/listeners are not independent replicates. No significance claim, calibration or plateau is established.",
            "tie_policy": "Listener and objective ties reported separately, excluded from decisive fractions; unequal objective coverage is inconclusive; unknown preferences are not inferred."}
