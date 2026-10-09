"""Synthetic-only precision intervention; no dataset/model/array-file access."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FFTS = (256, 512, 1024, 2048, 4096)
TOL = 1e-8
SOURCES = (
    "learn/di_domain_metric_probe.py", "tests/test_di_domain_metric_probe.py",
    "docs/di-domain-metric-probe-plan.md", "docs/di-domain-pilot-metric.json",
    "learn/direc.py", "learn/di_domain_pilot.py", "learn/__init__.py",
)


def write_new(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def guard():
    if "**Declared:" not in (ROOT / "docs/di-domain-metric-probe-plan.md").read_text():
        raise ValueError("synthetic probe not declared")
    pins = {}
    for name in SOURCES:
        data = (ROOT / name).read_bytes()
        committed = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        if data != committed:
            raise ValueError(f"uncommitted probe dependency: {name}")
        pins[name] = hashlib.sha256(data).hexdigest()
    return pins


def window_record(window, dtype):
    """Lossless IEEE bits and canonical byte hash; no learned or audio material."""
    import numpy as np

    x = np.asarray(window, dtype=np.dtype(dtype))
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError("invalid synthetic window")
    integer = "<u4" if x.dtype.itemsize == 4 else "<u8"
    if x.dtype not in (np.dtype("<f4"), np.dtype("<f8")):
        raise ValueError("only float32/float64 coefficients allowed")
    return {"dtype": x.dtype.str, "bits": x.view(integer).tolist(),
            "sha256": hashlib.sha256(x.tobytes()).hexdigest()}


def numpy_terms(a, b, windows):
    import numpy as np

    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.ndim != 1 or a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("matching finite mono synthetic signals required")
    terms, loss = [], 0.0
    for n, supplied in windows.items():
        window = np.asarray(supplied, np.float64)
        if window.shape != (n,) or not np.isfinite(window).all() or len(a) <= n//2:
            raise ValueError("invalid supplied coefficient array")

        def magnitude(x):
            frames = np.lib.stride_tricks.sliding_window_view(np.pad(x, n//2, mode="reflect"), n)[::n//4]
            return np.abs(np.fft.rfft(frames * window, axis=-1)) + 1e-6

        A, B = magnitude(a), magnitude(b)
        sc = float(np.linalg.norm(A-B) / (np.linalg.norm(B)+1e-6))
        log = float(np.mean(np.abs(np.log(A)-np.log(B))))
        terms.append({"fft": n, "spectral_convergence": sc, "log_l1": log, "total": sc+log})
        loss += sc + log
    if not terms:
        raise ValueError("empty coefficient mapping")
    return {"aggregate": loss / len(terms), "terms": terms}


def torch_terms(a, b, windows):
    import torch

    a, b = torch.from_numpy(a)[None], torch.from_numpy(b)[None]
    terms, loss = [], 0.0
    for n, window in windows.items():
        A = torch.stft(a, n, n//4, window=window, return_complex=True).abs() + 1e-6
        B = torch.stft(b, n, n//4, window=window, return_complex=True).abs() + 1e-6
        sc = (A-B).norm() / (B.norm()+1e-6)
        log = (A.log()-B.log()).abs().mean()
        loss = loss + sc + log  # Preserve the frozen function's operation order.
        terms.append({"fft": n, "spectral_convergence": float(sc), "log_l1": float(log), "total": float(sc+log)})
    return {"aggregate": float(loss / len(terms)), "terms": terms}


def terms_agree(first, second):
    if len(first["terms"]) != len(second["terms"]):
        return False
    for a, b in zip(first["terms"], second["terms"]):
        if a["fft"] != b["fft"]:
            return False
        for key in ("spectral_convergence", "log_l1", "total"):
            if not math.isfinite(a[key]) or not math.isfinite(b[key]) or abs(a[key]-b[key]) > TOL:
                return False
    return math.isfinite(first["aggregate"]) and math.isfinite(second["aggregate"]) and abs(first["aggregate"]-second["aggregate"]) <= TOL


def case_checks(row, original):
    numpy, torch = row["original_numpy"], row["original_torch"]
    discrepancy = torch-numpy
    explained = row["numpy_t32"]["aggregate"]-numpy
    return {
        "reproduced": abs(numpy-original["numpy"]) <= 1e-12 and abs(torch-original["torch"]) <= 1e-12,
        "same_original_pass_pattern": (abs(discrepancy) <= TOL) == (original["absolute_error"] <= TOL),
        "explicit_t32_equals_frozen_exactly": row["torch_t32"]["aggregate"] == torch,
        "explicit_np64_matches_original": abs(row["numpy_np64"]["aggregate"]-numpy) <= 1e-12,
        "shared_t32_components_agree": terms_agree(row["numpy_t32"], row["torch_t32"]),
        "shared_np64_components_agree": terms_agree(row["numpy_np64"], row["torch_np64"]),
        "signed_intervention_accounts_for_error": abs(explained-discrepancy) <= TOL,
    }


def probe(output, pins):
    import numpy as np
    import torch
    from learn import direc as D
    from learn import di_domain_pilot as P

    started = time.monotonic()
    torch.set_num_threads(2)
    original = json.loads((ROOT / "docs/di-domain-pilot-metric.json").read_text())
    versions = {"python": sys.version, "torch": torch.__version__, "torch_build": torch.version.git_version,
                "numpy": np.__version__, "threads": torch.get_num_threads(), "device": "cpu",
                "default_dtype": str(torch.get_default_dtype()), "input_dtype": "float64"}
    write_new(output / "provenance.json", {"pins": pins, "versions": versions})
    if torch.get_default_dtype() != torch.float32:
        raise ValueError("unexpected default dtype; stop for review")
    np64, t32, t64, exported = {}, {}, {}, {}
    for n in FFTS:
        np64[n] = 0.5 - 0.5*np.cos(2*np.pi*np.arange(n)/n)
        t32[n] = torch.hann_window(n, periodic=True, dtype=torch.float32, device="cpu")
        t64[n] = torch.hann_window(n, periodic=True, dtype=torch.float64, device="cpu")
        default = torch.hann_window(n, device="cpu")
        exported[str(n)] = {
            "np64": window_record(np64[n], "<f8"), "torch32": window_record(t32[n].numpy(), "<f4"),
            "torch64": window_record(t64[n].numpy(), "<f8"),
            "default_equals_explicit32": bool(torch.equal(default, t32[n])),
            "default_hann_dtype": str(default.dtype),
            "numpy_cast32_equals_torch32": bool(np.array_equal(np64[n].astype(np.float32), t32[n].numpy())),
            "max_np64_vs_torch32": float(np.max(np.abs(np64[n]-t32[n].numpy()))),
            "max_np64_vs_torch64": float(np.max(np.abs(np64[n]-t64[n].numpy()))),
        }
    write_new(output / "windows.json", exported)
    shared32 = {n: t.numpy().astype(np.float64) for n, t in t32.items()}
    shared_np64 = {n: torch.from_numpy(w) for n, w in np64.items()}
    rng = np.random.default_rng(20261008)
    b = rng.normal(size=144000) * .1
    rows = []
    with torch.no_grad():
        for index, a in enumerate((b.copy(), b*.5, np.roll(b,52), np.zeros_like(b))):
            if time.monotonic()-started > 900:
                raise TimeoutError("cooperative 15-minute probe budget exceeded")
            row = {"index": index, "original_numpy": P.mrstft_numpy(a,b),
                   "original_torch": float(D.mrstft(torch.from_numpy(a)[None], torch.from_numpy(b)[None])),
                   "numpy_t32": numpy_terms(a,b,shared32), "torch_t32": torch_terms(a,b,t32),
                   "numpy_np64": numpy_terms(a,b,np64), "torch_np64": torch_terms(a,b,shared_np64),
                   "torch_t64": torch_terms(a,b,t64)}
            row["checks"] = case_checks(row, original["rows"][index])
            row["torch64_diagnostic_agreement"] = terms_agree(row["numpy_np64"], row["torch_t64"])
            row["stft_output_dtype"] = str(torch.stft(torch.from_numpy(a), 256, 64,
                window=t32[256], return_complex=True).dtype)
            rows.append(row)
            write_new(output / f"case-{index}.json", row)
            print(json.dumps({"case": index, "checks": row["checks"]}), flush=True)
    if torch.get_default_dtype() != torch.float32:
        raise ValueError("global default dtype changed")
    passed = all(r["default_equals_explicit32"] for r in exported.values()) and all(all(r["checks"].values()) for r in rows)
    write_new(output / "result.json", {"passed": passed, "rows": rows, "elapsed_seconds": time.monotonic()-started})
    if not passed:
        raise ValueError("window intervention did not establish the declared explanation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pins = guard()
    output = args.out.resolve()
    if not output.is_relative_to((ROOT / "tmp").resolve()):
        raise ValueError("probe output must remain in project tmp")
    output.mkdir(parents=True, exist_ok=False)
    try:
        probe(output, pins)
    except Exception as error:
        write_new(output / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    main()
