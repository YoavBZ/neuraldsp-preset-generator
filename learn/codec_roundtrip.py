"""The codec ceiling's round trips (`docs/scratch-search-plan.md` section 12, "The `fs-codec` row"; ledger
`preset-ladder` `phase_scratch_codec`).

Runs on the CPU in a codec's own interpreter and imports nothing from this project (the pattern of
`learn/dac_roundtrip.py`); torch, numpy and each codec are imported inside the function that needs them, so the pure
rules run on the light CI runner and under Python 3.9 (`dac-venv`).

    ~/ndsp-presets/tools/codec-venv/bin/python learn/codec_roundtrip.py --codecs rt-m2l rt-m2l-b rt-id \\
        --inp PF/fs/codec/in --out PF/fs/codec/out --models ~/ndsp-presets/tools/codec-models
    ~/ndsp-presets/tools/dac-venv/bin/python learn/codec_roundtrip.py --codecs rt-dac rt-rs \\
        --inp PF/fs/codec/in --out PF/fs/codec/out --models ~/ndsp-presets/tools/codec-models

Input (`learn.scratch_codec prep`): one float32 `.npy` a part in `--inp`, 48 kHz, IN_LEN samples (the raw DI section
with TRIM before it, then the DI file's own next second, zeros only where the file ends), and `in.json` naming each
file's sha256 and the section's SECTION samples. Output: `<out>/<name>/<pkey>.npy` (float32, 48 kHz, SECTION samples,
at the input's level) and `<out>/roundtrip-<venv>.json` (package versions, each weight file's sha256 checked against
`manifest.json` and the declared value, seeds, threads, device, seconds a part). Nothing is overwritten.

- `rt-m2l`, `rt-m2l-b`: `linear_cae.Autoencoder.from_pretrained("m2l")` (Apache-2.0), fed 48 kHz as it is (LOUDAR's
  use), LOUDAR's level rule in (`loudar_gain`) and undone after, the input zero-padded to `pad_len`, encoded, decoded
  in one denoising step with `torch.manual_seed(seed_of(s, j))` just before the decode, cut to SECTION.
- `rt-dac`: DAC 44.1 kHz, 8 kbps, 9 codebooks, as `learn/dac_roundtrip.py`: peak 0.5 in and restored, 48 -> 44.1 ->
  48 kHz by `resample_poly` (147/160, 160/147), cut to SECTION.
- `rt-rs`: that resampling alone. `rt-id`: the first SECTION samples unchanged.

No weight file is ever loaded with `weights_only=False`: `TORCH_FORCE_WEIGHTS_ONLY_LOAD=1` is set before torch is
imported, and each weight file's sha256 is checked before any load. `HF_HOME` is set here to `<--models>/hf` with
`HF_HUB_OFFLINE=1` (`set_hf_env`; an HF_HOME set elsewhere is refused), so the operator sets neither.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import time

SR = 48000
DAC_SR = 44100
SECTION = 492000                 # pretrain_set: (SEC_S + TRIM_S) * SR
NEXT = 48000                     # the DI file's own next second
IN_LEN = SECTION + NEXT          # 540,000
RT_SEED = 20261601               # main's seeds end at 20261403; the note-reader plan claims 20261411 and 20261412
M2L_HOP = 4096                   # Music2Latent's latent frame: 4,096 samples
M2L_EXTRA = 1536                 # its input is 4,096 k + 1,536 samples
LOUDAR_RMS_DB = -18.0            # LOUDAR's guitar config: rms_normalize -18 (compute_log_rms_gated_max)
LOUDAR_SEG_S, LOUDAR_HOP_S = 0.4, 0.1
LOUDAR_FLOOR = 1e-8
DAC_PEAK = 0.5
DAC_CODEBOOKS = 9
THREADS = 4
VENVS = {"codec": ("rt-m2l", "rt-m2l-b", "rt-id"), "dac": ("rt-dac", "rt-rs")}
NAMES = ("rt-m2l", "rt-m2l-b", "rt-dac", "rt-id", "rt-rs")
SEED_SLOT = {"rt-m2l": 0, "rt-m2l-b": 1}  # seed_of's s: decode seed a, decode seed b
M2L_REPO = "BernardoTorres/linear_consistency_autoencoders"
M2L_DIR = "1511f18a_weights"
M2L_FILES = ("autoencoder_inference_model_last.pth", "frontend_kwargs_last.yaml", "generator_kwargs_last.yaml",
             "diffusion_kwargs_last.yaml")
DAC_WEIGHTS = pathlib.Path("~/.cache/descript/dac/weights_44khz_8kbps_0.0.1.pth").expanduser()   # as E0/E0b, 0c
DECLARED_SHA256 = {                  # the plan's, from the Hugging Face API and the file on disk
    "m2l/autoencoder_inference_model_last.pth": "405499f959fbbe38496fa2c0cc5663b495058a353157304006bff5bfced5b20b",
    "dac/weights_44khz_8kbps_0.0.1.pth": "a88eed82a7024ccc1facdb1e605c4c2f99281c8118c22c9895ffa846d8fb61aa",
}


# --- the pure rules ------------------------------------------------------------------------------------------------------

def pad_len(n):
    """(Pure.) The least 4,096 k + 1,536 at or above n: Music2Latent's input length (542,208 for 540,000)."""
    if n <= M2L_EXTRA:
        return M2L_EXTRA
    return M2L_HOP * math.ceil((n - M2L_EXTRA) / M2L_HOP) + M2L_EXTRA


def seed_of(s, j):
    """(Pure.) The decode seed: RT_SEED + 1000 s + j; s is 0 for `rt-m2l`, 1 for `rt-m2l-b`; j the part's index in
    the sorted keys."""
    return RT_SEED + 1000 * s + j


def venv_of(names):
    """(Pure.) The interpreter a set of names runs in: "codec" or "dac"; refuses a mix or an unknown name."""
    got = {v for v, ns in VENVS.items() for n in names if n in ns}
    bad = [n for n in names if n not in NAMES]
    if bad or len(got) != 1 or not names:
        raise SystemExit(f"--codecs {list(names)}: one venv's names only ({VENVS})")
    return got.pop()


def weight_refusal(key, sha, manifest):
    """(Pure.) Why a weight file may not be loaded, or None: its sha256 must equal the manifest's entry for `key` and,
    where the plan declares one, the declared value. manifest: {"files": {key: {"sha256", ...}}}."""
    ent = ((manifest or {}).get("files") or {}).get(key)
    if not isinstance(ent, dict) or not ent.get("sha256"):
        return f"{key}: not in manifest.json"
    if ent["sha256"] != sha:
        return f"{key}: sha256 {sha[:12]} is not the manifest's {ent['sha256'][:12]}"
    want = DECLARED_SHA256.get(key)
    if want is not None and want != sha:
        return f"{key}: sha256 {sha[:12]} is not the declared {want[:12]}"
    return None


def input_refusal(rec, key, sha, n):
    """(Pure.) Why an input file may not be round-tripped, or None: in.json's sha256 and IN_LEN samples."""
    ent = ((rec or {}).get("parts") or {}).get(key)
    if not isinstance(ent, dict) or ent.get("sha256") != sha:
        return f"{key}: not the file in.json names"
    if n != IN_LEN:
        return f"{key}: {n} samples, not {IN_LEN}"
    return None


# --- the numpy rules -------------------------------------------------------------------------------------------------------

def loudar_gain(x, sr=SR):
    """LOUDAR's level rule in numpy (`compute_log_rms_gated_max` and `apply_RMS_normalization`): frames of 0.4 s with
    a hop of 0.1 s as torch's `unfold` (no padding, the tail dropped), each frame's RMS in dB floored at 1e-8, the
    **loudest** frame brought to -18 dB. -> the linear gain, 10 ** (gain_db / 20 + 1e-6) as LOUDAR writes it. Reads
    the samples given (the section's SECTION only)."""
    import numpy as np

    seg, hop = int(sr * LOUDAR_SEG_S), int(sr * LOUDAR_HOP_S)
    x = np.asarray(x, np.float64)
    if len(x) < seg:
        raise ValueError(f"{len(x)} samples: shorter than one {seg}-sample frame")
    n = (len(x) - seg) // hop + 1
    frames = np.lib.stride_tricks.sliding_window_view(x, seg)[::hop][:n]
    rms = np.sqrt((frames ** 2).mean(axis=1))
    rms_db = 20 * np.log10(np.maximum(rms, LOUDAR_FLOOR))
    return float(10 ** ((LOUDAR_RMS_DB - rms_db.max()) / 20 + 1e-6))


def to44(x):
    from scipy.signal import resample_poly

    return resample_poly(x, 147, 160)


def to48(x, n):
    import numpy as np
    from scipy.signal import resample_poly

    y = resample_poly(x, 160, 147)[:n]
    return np.pad(y, (0, n - len(y))) if len(y) < n else y


def cut(y, n=SECTION):
    """The section's first n samples, as float32; refuses a shorter output."""
    import numpy as np

    y = np.asarray(y).reshape(-1)
    if len(y) < n:
        raise SystemExit(f"the codec returned {len(y)} samples, fewer than {n}")
    return np.asarray(y[:n], np.float32)


def rt_identity(x):
    return cut(x)


def rt_resample(x):
    """`rt-rs`: 48 -> 44.1 -> 48 kHz at DAC's input level, no codec."""
    import numpy as np

    x = np.asarray(x, np.float64)
    peak = float(np.abs(x).max()) + 1e-12
    return cut(to48(to44(x / peak * DAC_PEAK), len(x)) / DAC_PEAK * peak)


# --- the codecs (torch inside) ---------------------------------------------------------------------------------------------

def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def safe_torch():
    """Torch with every load forced to weights_only=True (set before the import), CPU, THREADS threads."""
    if os.environ.get("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "0").lower() in ("1", "y", "yes", "true"):
        raise SystemExit("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD is set: no weight file is loaded with weights_only=False")
    os.environ["TORCH_FORCE_WEIGHTS_ONLY_LOAD"] = "1"
    import torch

    torch.set_num_threads(THREADS)
    return torch


def hf_home(models):
    """(Pure.) The Hugging Face cache the round trips read: `<--models>/hf` (unit 0 fetches m2l there)."""
    return pathlib.Path(models) / "hf"


def set_hf_env(models, env=None):
    """HF_HOME set to `hf_home(models)` and HF_HUB_OFFLINE=1 before huggingface_hub is imported; refuses a missing
    cache, or an HF_HOME already set elsewhere, rather than reaching another cache or the network."""
    env = os.environ if env is None else env
    want = hf_home(models)
    if env.get("HF_HOME") and pathlib.Path(env["HF_HOME"]).expanduser().resolve() != want.expanduser().resolve():
        raise SystemExit(f"HF_HOME is {env['HF_HOME']}, not {want}: unset it (the round trips set it themselves)")
    if not want.is_dir():
        raise SystemExit(f"no Hugging Face cache at {want}: fetch m2l there first (unit 0)")
    env["HF_HOME"] = str(want)
    env["HF_HUB_OFFLINE"] = "1"
    return want


def load_m2l(manifest, models):
    """`m2l` from the local Hugging Face cache under `<--models>/hf` only (HF_HOME set here, HF_HUB_OFFLINE=1), every
    file's sha256 checked first."""
    set_hf_env(models)
    torch = safe_torch()
    from huggingface_hub import hf_hub_download
    from linear_cae import Autoencoder

    shas = {}
    for f in M2L_FILES:
        path = hf_hub_download(repo_id=M2L_REPO, filename=f"{M2L_DIR}/{f}", local_files_only=True)
        key = f"m2l/{f}"
        shas[key] = file_sha(path)
        why = weight_refusal(key, shas[key], manifest)
        if why:
            raise SystemExit(why)
    model = Autoencoder.from_pretrained("m2l").eval()
    dev = {p.device.type for p in model.parameters()}
    if dev != {"cpu"}:
        raise SystemExit(f"m2l is on {dev}, not the CPU")
    return torch, model, shas


def rt_m2l(torch, model, x, seed):
    """One `m2l` round trip: LOUDAR's gain on the section, zero-padded to `pad_len`, encode, a seeded one-step decode,
    the gain undone, cut to SECTION."""
    import numpy as np

    x = np.asarray(x, np.float64)
    g = loudar_gain(x[:SECTION])
    xin = np.pad(x * g, (0, pad_len(len(x)) - len(x)))
    with torch.no_grad():
        t = torch.tensor(xin, dtype=torch.float32)[None]
        z = model.encode(t)
        torch.manual_seed(seed)
        y = model.decode(z, full_length=len(xin))
    y = y.detach().cpu().numpy().reshape(-1).astype(np.float64)
    return cut(y / g), {"gain": g, "latent_shape": list(z.shape)}


def load_dac(manifest):
    torch = safe_torch()
    import dac

    if not DAC_WEIGHTS.exists():
        raise SystemExit(f"no DAC weights at {DAC_WEIGHTS}; downloading them needs the user's yes")
    key = f"dac/{DAC_WEIGHTS.name}"
    shas = {key: file_sha(DAC_WEIGHTS)}
    why = weight_refusal(key, shas[key], manifest)
    if why:
        raise SystemExit(why)
    model = dac.DAC.load(str(DAC_WEIGHTS)).eval()
    return torch, model, shas


def rt_dac(torch, model, x):
    """One DAC round trip, as `learn/dac_roundtrip.py`'s `encode` with 9 codebooks: peak 0.5 in (the whole input the
    codec sees) and restored, 48 -> 44.1 -> 48 kHz, cut to SECTION."""
    import numpy as np

    x = np.asarray(x, np.float64)
    peak = float(np.abs(x).max()) + 1e-12
    x44 = to44(x / peak * DAC_PEAK)
    with torch.no_grad():
        t = torch.tensor(x44, dtype=torch.float32)[None, None]
        t = model.preprocess(t, DAC_SR)
        z = model.encode(t, n_quantizers=DAC_CODEBOOKS)[0]
        y = model.decode(z)[0, 0].numpy()
    return cut(to48(y[:len(x44)], len(x)) / DAC_PEAK * peak), {"peak": peak}


def versions(venv):
    from importlib import metadata

    pk = ("torch", "numpy", "scipy") + (("linear-cae", "huggingface-hub") if venv == "codec" else
                                         ("descript-audio-codec", "descript-audiotools"))
    out = {}
    for p in pk:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = None
    return out


def main(argv=None):
    import platform

    import numpy as np

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inp", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--codecs", nargs="+", required=True)
    ap.add_argument("--models", type=pathlib.Path, required=True)
    a = ap.parse_args(argv)
    inp, out, models = a.inp.expanduser(), a.out.expanduser(), a.models.expanduser()
    venv = venv_of(a.codecs)
    rec_p = out / f"roundtrip-{venv}.json"
    if rec_p.exists():
        raise SystemExit(f"{rec_p} exists: never overwritten")
    in_rec = json.loads((inp / "in.json").read_text())
    manifest = json.loads((models / "manifest.json").read_text())
    keys = sorted(in_rec["parts"])
    for name in a.codecs:
        for k in keys:
            if (out / name / f"{k}.npy").exists():
                raise SystemExit(f"{out / name / k}.npy exists: never overwritten")
    torch, model, shas = None, None, {}
    if any(n in SEED_SLOT for n in a.codecs):
        torch, model, shas = load_m2l(manifest, models)
    elif "rt-dac" in a.codecs:
        torch, model, shas = load_dac(manifest)
    seconds = {n: [] for n in a.codecs}
    seeds, notes = {}, {n: {} for n in a.codecs}
    for j, k in enumerate(keys):
        f = inp / f"{k}.npy"
        why = input_refusal(in_rec, k, file_sha(f), len(np.load(f)))
        if why:
            raise SystemExit(why)
        x = np.load(f).astype(np.float64)
        for name in a.codecs:
            t0 = time.time()
            if name == "rt-id":
                y, note = rt_identity(x), {}
            elif name == "rt-rs":
                y, note = rt_resample(x), {}
            elif name == "rt-dac":
                y, note = rt_dac(torch, model, x)
            else:
                s = seed_of(SEED_SLOT[name], j)
                seeds.setdefault(name, {})[k] = s
                y, note = rt_m2l(torch, model, x, s)
            seconds[name].append(time.time() - t0)
            if not np.isfinite(y).all():
                raise SystemExit(f"{name} {k}: a non-finite output")
            (out / name).mkdir(parents=True, exist_ok=True)
            np.save(out / name / f"{k}.npy", y)
            notes[name][k] = dict(note, sha256=file_sha(out / name / f"{k}.npy"))
        print(f"{j + 1}/{len(keys)} {k[-50:]}: " + ", ".join(f"{n} {seconds[n][-1]:.1f} s" for n in a.codecs),
              flush=True)
    res = {"plan": "docs/scratch-search-plan.md section 12", "venv": venv, "python": platform.python_version(),
           "versions": versions(venv), "weights_sha256": shas, "manifest_sha256": file_sha(models / "manifest.json"),
           "in_json_sha256": file_sha(inp / "in.json"), "codecs": list(a.codecs), "seeds": seeds,
           "threads": THREADS, "device": "cpu", "torch_force_weights_only": os.environ.get(
               "TORCH_FORCE_WEIGHTS_ONLY_LOAD"),
           "seconds_a_part": {n: sum(v) / len(v) for n, v in seconds.items() if v}, "parts": notes,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    out.mkdir(parents=True, exist_ok=True)
    rec_p.write_text(json.dumps(res, indent=1))
    print(f"ROUNDTRIP DONE {venv}: {len(keys)} parts; seconds a part {res['seconds_a_part']}")


if __name__ == "__main__":
    main()
