"""Bounded saved-waveform scoring-coordinate sensitivity; DRAFT until review.

No inference, rendering, average, native inputs, alignment fitting or training.
Importing this module reads no study artifacts. Only main may declare/run it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import di_morgan_flatref as F
from learn import di_domain_pilot as P
from learn import run_di_domain_pilot as R
from learn import run_di_domain_pilot_v2 as V

PLAN = ROOT / "docs/di-timing-sensitivity-plan.md"
HASHES = ROOT / "docs/di-timing-sensitivity-inputs.sha256"
SOURCE = ROOT / "tmp/di-morgan-control-20261008"
FLAT = ROOT / "tmp/di-morgan-flatref-20261008"
OUTPUT = "tmp/di-timing-sensitivity-20261008"
REVIEW = "docs/research/di-timing-sensitivity-review-2026-10-08.md"
VERIFIER = "docs/research/di-morgan-flatref-independent-2026-10-08.py"
CONTROL_VERIFIER = "docs/research/di-morgan-control-independent-2026-10-08.py"
OWN_PINS = (
    "learn/di_timing_sensitivity.py", "tests/test_di_timing_sensitivity.py",
    "docs/di-timing-sensitivity-plan.md", "docs/di-timing-sensitivity-inputs.sha256",
    REVIEW, VERIFIER, CONTROL_VERIFIER, "docs/di-morgan-flatref.json",
    "docs/di-morgan-flatref-verification.json", "docs/di-morgan-flatref-provenance.json",
)
OFFSETS = (-128, -52, -16, -8, -3, -2, 0, 2, 3, 8, 16, 52, 128)
SMALL = (-3, -2, 2, 3)
ARMS = {"wet": "input_scores", "net": "network_scores", "flatref": "flatref_scores"}
METRICS = ("primary", "canonical_waveform_l1", "raw_lowband")
TOL = 1e-8


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def design_bytes(text):
    return text.split("## Frozen design\n", 1)[1].encode()


def identity(row):
    return {key: row[key] for key in ("slug", "content", "take")}


def panel(takes):
    if (len(takes) != 12 or len({t["slug"] for t in takes}) != 12
            or len({t["take"] for t in takes}) != 12
            or any(t["content"] not in ("chords", "scales") for t in takes)
            or any(sum(t["content"] == g for t in takes) != 6 for g in ("chords", "scales"))
            or any(not re.fullmatch(r"[a-zA-Z0-9_-]+", t["slug"]) for t in takes)):
        raise ValueError("require twelve distinct declared takes, six per content group")


def coverage(rows, takes):
    return len(rows) == 12 and [identity(r) for r in rows] == [identity(t) for t in takes]


def loss(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def close(a, b):
    """Strict structure/boolean identity, absolute tolerance for finite numbers."""
    if type(a) is dict and type(b) is dict:
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if type(a) is list and type(b) is list:
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if type(a) in (int, float) and type(b) in (int, float):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b) <= TOL
    return type(a) is type(b) and a == b


def validate_row(row):
    if row.get("qc_valid") is not True or not loss(row["oracle"]) or row["oracle"] >= 1e-6:
        raise ValueError("invalid inherited QC/oracle")
    for arm, key in ARMS.items():
        if (set(row[key]) != set(METRICS) or not all(loss(v) for v in row[key].values())
                or row[arm] != row[key]["primary"]):
            raise ValueError("invalid score keys, values or primary scalar")
    if min(row["wet"], row["flatref"]) <= 0:
        raise ValueError("positive simple denominators required")


def prerequisite(original, verification, prepare, control, takes, inherited, pins):
    """Metadata only; all twelve prior QC/oracles and independent wave identities."""
    panel(takes)
    if (original.get("complete") is not True or not coverage(original.get("rows", []), takes)
            or original["screen"].get("passed") is not True):
        raise ValueError("complete passed original flatref prerequisite required")
    for row in original["rows"]:
        validate_row(row)
    if not close(F.compare(original["rows"], takes), original["screen"]):
        raise ValueError("original stronger screen mismatch")
    checks = verification.get("checks", [])
    if (verification.get("status") != "VERIFIED_WITH_EVIDENCE_LIMITS"
            or verification.get("failures") != [] or len(checks) != 1215
            or any(c.get("passed") is not True for c in checks)
            or verification.get("source_pins") != inherited
            or verification.get("verifier_sha256") != pins[VERIFIER]
            or not close(verification.get("independent_screen"), original["screen"])
            or not coverage(verification.get("independent_rows", []), takes)):
        raise ValueError("successful independent flatref verification with 1215 checks required")
    for a, b in zip(original["rows"], verification["independent_rows"]):
        if not close(a, {k: b[k] for k in a}):
            raise ValueError("independent original score/QC identity mismatch")
    waves = verification.get("waveform_comparison", [])
    if len(waves) != 12 or [r["slug"] for r in waves] != [t["slug"] for t in takes]:
        raise ValueError("all twelve independent waveform identities required")
    for w, row in zip(waves, verification["independent_rows"]):
        if (w.get("byte_identical") is not True or w.get("max_absolute_error") != 0
                or not re.fullmatch(r"[a-f0-9]{64}", w["primary_sha256_float64"])
                or w["primary_sha256_float64"] != row["flatref_waveform_sha256_float64"]
                or w["npz_sha256"] != verification["primary_artifact_hashes"][w["slug"]+".npz"]):
            raise ValueError("independent waveform identity mismatch")
    if (prepare.get("complete") is not True or prepare.get("valid") is not True
            or not coverage(prepare.get("rows", []), takes)
            or not coverage(control.get("preparation", []), takes)
            or not coverage(control.get("replay", []), takes)
            or control.get("verifier_sha256") != pins[CONTROL_VERIFIER]):
        raise ValueError("complete verified prior preparation/prediction identities required")
    for p, v, row in zip(prepare["rows"], control["preparation"], original["rows"]):
        if (p.get("qc_valid") is not True or p["qc"].get("valid") is not True
                or v["qc"].get("valid") is not True or not close(p["qc"], v["qc"])
                or not loss(p["oracle_scores"]["primary"])
                or p["oracle_scores"]["primary"] >= 1e-6
                or not close(p["oracle_scores"], v["oracle_scores"])
                or not close(row["oracle"], p["oracle_scores"]["primary"])):
            raise ValueError("all twelve original verified QC/oracles required")


def declared_hashes(takes, original, verification):
    """Exact original36 plus verified saved12; never discover or hash assets here."""
    panel(takes)
    old = {str((SOURCE / stage / f"{t['slug']}.npz").relative_to(ROOT))
           for stage in ("prepare", "render", "infer") for t in takes}
    flat = {str((FLAT / f"{t['slug']}.npz").relative_to(ROOT)) for t in takes}
    expected, observed = old | flat, {}
    for line in HASHES.read_text().splitlines():
        parts = line.split("  ")
        if len(parts) != 2:
            raise ValueError("invalid artifact hash syntax")
        sha, name = parts
        if name not in expected or name in observed or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError("invalid, duplicate or undeclared artifact hash")
        observed[name] = sha
    if set(observed) != expected or len(observed) != 48:
        raise ValueError("require exactly all 48 verified artifacts")
    subset = {n: observed[n] for n in old}
    if subset != original["input_artifacts"] or subset != verification["input_artifacts"]:
        raise ValueError("original36 artifact identity subset changed")
    for name in flat:
        if observed[name] != verification["primary_artifact_hashes"][Path(name).name]:
            raise ValueError("saved12 flatref artifact identity changed")
    return observed


def guard():
    text = PLAN.read_text()
    match = re.search(r"<!-- timing-approval\n(.*?)\ntiming-approval -->", text, re.S)
    approval = json.loads(match[1]) if match else {}
    if ("**Declared:" not in text or approval.get("status") != "DECLARED"
            or approval.get("fresh_independent_review") is not True
            or approval.get("scope") != "common-post-inference-coordinate-only"):
        raise ValueError("requires fresh independent review and committed declaration")
    correction, manifest, inherited, _ = F.guard()
    if len(inherited) != 43 or set(inherited) & set(OWN_PINS):
        raise ValueError("expected exactly 43 disjoint inherited source pins")
    pins = dict(inherited)
    for name in OWN_PINS:
        data = (ROOT / name).read_bytes()
        if data != subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT):
            raise ValueError(f"uncommitted timing dependency: {name}")
        pins[name] = digest(data)
    expected = {"review_sha256": pins[REVIEW],
                "source_sha256": pins["learn/di_timing_sensitivity.py"],
                "test_sha256": pins["tests/test_di_timing_sensitivity.py"],
                "design_sha256": digest(design_bytes(text)),
                "inputs_sha256": pins["docs/di-timing-sensitivity-inputs.sha256"]}
    if any(approval.get(k) != v for k, v in expected.items()):
        raise ValueError("fresh review does not identify this exact snapshot")
    if "Verdict: APPROVE" not in (ROOT / REVIEW).read_text():
        raise ValueError("fresh independent review approval required")
    original = read_json(ROOT / "docs/di-morgan-flatref.json")
    verification = read_json(ROOT / "docs/di-morgan-flatref-verification.json")
    prepare = read_json(ROOT / "docs/di-morgan-control-prepare.json")
    control = read_json(ROOT / "docs/di-morgan-control-verification.json")
    prerequisite(original, verification, prepare, control, manifest["takes"], inherited, pins)
    for name, archive in (("result.json", "docs/di-morgan-flatref.json"),
                          ("provenance.json", "docs/di-morgan-flatref-provenance.json")):
        if ((FLAT / name).read_bytes() != (ROOT / archive).read_bytes()
                or pins[archive] != verification["primary_artifact_hashes"][name]):
            raise ValueError("verified original flatref report/provenance changed")
    if read_json(FLAT / "provenance.json").get("pins") != inherited:
        raise ValueError("original flatref 43 provenance pins changed")
    hashes = declared_hashes(manifest["takes"], original, verification)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return correction, manifest, pins, revision, original, verification, control, hashes


def recheck_sources(pins, revision, started):
    for name, sha in pins.items():
        R.check_time(started)
        if digest((ROOT / name).read_bytes()) != sha:
            raise ValueError(f"source/input metadata drift: {name}")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != revision:
        raise ValueError("HEAD changed during diagnostic")


def check_artifacts(hashes, started):
    for name, sha in hashes.items():
        R.check_time(started)
        path = ROOT / name
        if path.resolve() != path or not path.is_file() or R.sha(path) != sha:
            raise ValueError(f"changed or linked verified artifact: {name}")


def wave_hash(x, dtype):
    import numpy as np
    return digest(np.asarray(x, dtype=dtype).tobytes())


def load_inputs(takes, hashes, verification, control, started):
    import numpy as np

    check_artifacts(hashes, started)  # ALL48 barrier before the first np.load.
    loaded, identities = {}, {}
    waves = {r["slug"]: r for r in verification["waveform_comparison"]}
    prepared = {r["slug"]: r for r in control["preparation"]}
    predictions = {r["slug"]: r for r in control["replay"]}
    for take in takes:
        slug = take["slug"]
        values = {}
        for path, members in (
            (SOURCE / "prepare" / f"{slug}.npz", ("di", "target")),
            (SOURCE / "render" / f"{slug}.npz", ("baseline",)),
            (SOURCE / "infer" / f"{slug}.npz", ("prediction",)),
            (FLAT / f"{slug}.npz", ("flatref",)),
        ):
            check_artifacts({str(path.relative_to(ROOT)): hashes[str(path.relative_to(ROOT))]}, started)
            with np.load(path, allow_pickle=False) as saved:
                for member in members:  # Access only these five declared waveform members.
                    x = saved[member]
                    P._mono(x, P.SCORE)
                    std = float(np.std(x))
                    if x.dtype.kind != "f" or not math.isfinite(std) or std <= 0:
                        raise ValueError("nonfloating or silent saved waveform")
                    x.flags.writeable = False
                    values[member] = x
        if (values["prediction"].dtype != np.dtype("float32")
                or wave_hash(values["prediction"], "<f4") != predictions[slug]["prediction_sha256_float32"]
                or wave_hash(values["target"], "<f8") != prepared[slug]["target_sha256"]
                or values["flatref"].dtype != np.dtype("float64")
                or wave_hash(values["flatref"], "<f8") != waves[slug]["primary_sha256_float64"]):
            raise ValueError("verified target/prediction/flatref waveform identity mismatch")
        loaded[slug] = {"di": values["di"], "target": values["target"],
                        "wet": values["baseline"], "net": values["prediction"], "flatref": values["flatref"]}
        identities[slug] = {k: {"dtype": str(x.dtype), "samples": len(x),
                                  "sha256": digest(x.tobytes())} for k, x in loaded[slug].items()}
    check_artifacts(hashes, started)
    return loaded, identities


def finite_shift(x, offset):
    """Finite delay y[n] = x[n-offset] over the complete six seconds."""
    import numpy as np
    P._integer(offset, "offset")
    x = P._mono(x, P.SCORE)
    y = np.zeros_like(x)
    if offset == 0:
        y[:] = x
    elif 0 < offset < len(x):
        y[offset:] = x[:-offset]
    elif -len(x) < offset < 0:
        y[:offset] = x[-offset:]
    return y


def scored_row(take, saved, windows, previous, offset, started):
    row = {**identity(take), "offset": offset, "qc_valid": previous["qc_valid"],
           "oracle": previous["oracle"]}
    for arm, key in ARMS.items():
        R.check_time(started)
        wave = saved[arm] if offset == 0 else finite_shift(saved[arm], offset)
        row[key] = P.score_prediction(wave, saved["target"], saved["di"], windows=windows)
        row[arm] = row[key]["primary"]
        R.check_time(started)
    return row


def replay(out, takes, loaded, windows, original, started):
    rows, evidence, scalar_count = [], [], 0
    previous = {r["slug"]: r for r in original["rows"]}
    for take in takes:
        item = {**identity(take), "valid": False}
        try:
            row = scored_row(take, loaded[take["slug"]], windows, previous[take["slug"]], 0, started)
            item["scores"] = {key: row[key] for key in ARMS.values()}
            validate_row(row)
            errors = {f"{arm}.{m}": abs(row[key][m]-previous[take["slug"]][key][m])
                      for arm, key in ARMS.items() for m in METRICS}
            scalar_count += len(errors)
            rows.append(row)
            item.update(valid=True, errors=errors)
        except TimeoutError:
            raise
        except Exception as error:
            item["error"] = {"type": type(error).__name__, "message": str(error)}
        evidence.append(R.safe_rejected_row(item))
    screen = F.compare(rows, takes)
    passed = (scalar_count == 108 and all(r["valid"] for r in evidence)
              and all(v <= TOL for r in evidence for v in r["errors"].values())
              and screen.get("passed") is True and close(screen, original["screen"]))
    R.write_new(out / "baseline-replay.json", {"complete": True, "passed": passed,
        "scalar_count": scalar_count, "absolute_tolerance": TOL, "rows": evidence, "screen": screen})
    if not passed:
        raise ValueError("original108 replay/screen mismatch before any nonzero shift")
    return rows


def paired_changes(row, zero):
    changes = {}
    for arm, key in ARMS.items():
        before = zero[key]["primary"]
        delta = row[key]["primary"]-before
        changes[arm] = {"primary_absolute_change": delta,
                        "primary_relative_change": delta/before if before > 0 else None,
                        "canonical_waveform_l1_change": row[key]["canonical_waveform_l1"]-zero[key]["canonical_waveform_l1"],
                        "raw_lowband_change": row[key]["raw_lowband"]-zero[key]["raw_lowband"]}
    simple, simple0 = min(row["wet"], row["flatref"]), min(zero["wet"], zero["flatref"])
    changes["advantage"] = {"primary_absolute_change": (simple-row["net"])-(simple0-zero["net"]),
                            "primary_relative_change": (simple-row["net"])/simple-(simple0-zero["net"])/simple0}
    return changes


def compare(rows, takes):
    def invalid(reason, screens=None):
        return {"valid": False, "passed": False, "disposition": "INCONCLUSIVE",
                "reason": reason, "offset_screens": screens or []}
    screens = []
    try:
        panel(takes)
        expected = {(offset, t["slug"]) for offset in OFFSETS for t in takes}
        actual = {(r["offset"], r["slug"]): r for r in rows}
        if len(rows) != 156 or len(actual) != 156 or actual.keys() != expected:
            return invalid("require complete unique 13-offset by 12-take coverage")
        for offset in OFFSETS:
            subset = [actual[offset, t["slug"]] for t in takes]
            try:
                for row, take in zip(subset, takes):
                    if type(row["offset"]) is not int or identity(row) != identity(take) or row.get("valid") is not True:
                        raise ValueError("invalid offset/take identity or scoring error")
                    validate_row(row)
                screen = F.compare(subset, takes)
            except (KeyError, TypeError, ValueError, OverflowError):
                screen = {"valid": False, "passed": False, "disposition": "INCONCLUSIVE",
                          "reason": "invalid score/QC/oracle or scoring error"}
            screens.append({"offset": offset, "role": "prerequisite" if offset == 0 else
                            "robustness" if offset in SMALL else "diagnostic_only",
                            "screen": screen})
        if any(s["screen"].get("valid") is not True for s in screens):
            return invalid("invalid fixed-offset screen", screens)
        zero = next(s["screen"] for s in screens if s["offset"] == 0)
        if zero.get("passed") is not True:
            return invalid("zero-offset PASS prerequisite failed", screens)
        passed = all(s["screen"]["passed"] for s in screens if s["offset"] in SMALL)
        return {"valid": True, "passed": passed, "disposition": "PASS" if passed else "FAIL",
                "offset_screens": screens, "required_small_offsets": list(SMALL)}
    except (KeyError, TypeError, ValueError, OverflowError):
        return invalid("invalid coverage, nonfinite score or inherited QC/oracle", screens)


def output_directory(requested):
    expected = ROOT / OUTPUT
    if requested.absolute() != expected or expected.resolve() != expected:
        raise ValueError(f"only declared --out {OUTPUT} is allowed; no symlink aliases")
    expected.mkdir(parents=True, exist_ok=False)
    return expected


def run(out, context, started):
    correction, manifest, pins, revision, original, verification, control, hashes = context
    takes = manifest["takes"]
    R.write_new(out / "provenance.json", {"pins": pins, "git_revision": revision,
        "input_artifacts": hashes, "python": sys.version, "prefix": sys.prefix,
        "started_unix": time.time(), "budget_seconds": R.LIMIT,
        "packages": {n: R.package_version(n) for n in ("numpy", "scipy")},
        "offsets": list(OFFSETS), "required_small_offsets": list(SMALL),
        "attribution": manifest["attribution"], "scope": "common-post-inference-coordinate-only"})
    recheck_sources(pins, revision, started)
    windows = V.load_windows(correction)  # Exact archived Torch32 bits, no formula fallback.
    loaded, identities = load_inputs(takes, hashes, verification, control, started)
    R.write_new(out / "inputs.json", {"artifacts": hashes, "waveforms": identities})
    zero = replay(out, takes, loaded, windows, original, started)
    # Persisted complete successful replay is the barrier for ALL nonzero shifts.
    recheck_sources(pins, revision, started)
    check_artifacts(hashes, started)
    prior = {r["slug"]: r for r in zero}
    rows = []
    for offset in OFFSETS:
        for take in takes:
            R.check_time(started)
            base = prior[take["slug"]]
            row = {**identity(take), "offset": offset}
            try:
                row = dict(base) if offset == 0 else scored_row(
                    take, loaded[take["slug"]], windows, base, offset, started)
                validate_row(row)
                row.update(valid=True, changes_from_zero=paired_changes(row, base))
            except TimeoutError:
                raise
            except Exception as error:
                row.update(valid=False, error={"type": type(error).__name__, "message": str(error)})
                row = R.safe_rejected_row(row)
            rows.append(row)
            R.progress(out, row)
            R.check_time(started)
    recheck_sources(pins, revision, started)
    check_artifacts(hashes, started)
    R.check_time(started)
    R.write_new(out / "result.json", {"complete": True, "rows": rows,
        "screen": compare(rows, takes), "input_artifacts": hashes,
        "elapsed_seconds": time.monotonic()-started, "attribution": manifest["attribution"],
        "interpretation": "Scoring-coordinate sensitivity only; same-player dependent development cases; no native causation or product confirmation."})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise ValueError("use actual project helper environment")
    started = time.monotonic()
    context = guard()  # DRAFT refusal before coefficients, asset hashes or arrays.
    out = output_directory(args.out)
    try:
        run(out, context, started)
    except Exception as error:
        R.write_new(out / "failure.json", {"type": type(error).__name__, "message": str(error),
            "disposition": "INCONCLUSIVE", "elapsed_seconds": time.monotonic()-started})
        raise


if __name__ == "__main__":
    main()
