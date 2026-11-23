"""LOUDAR's runs for the `fs-loudar` row (`docs/scratch-search-plan.md` section 13, "The `fs-loudar` row"; ledger
`preset-ladder` `phase_scratch_loudar`).

Runs in `~/ndsp-presets/tools/loudar-venv` on the CPU and imports nothing from this project; LOUDAR's code
(`~/ndsp-presets/tools/loudar/src` at commit LOUDAR_COMMIT) is put on `sys.path` inside the functions that need it, and
torch, numpy, omegaconf, hydra and LOUDAR's modules are imported there too, so the pure rules run on the light CI
runner.

    $LV learn/loudar_run.py run --inp PF/fs/loudar/in/ld-stem --out PF/fs/loudar/out/ld-stem --sets bks panel \\
        --setting <the gate's> --seed-slot 0 --models ~/ndsp-presets/tools/codec-models \\
        --code ~/ndsp-presets/tools/loudar
    $LV learn/loudar_run.py gate --code ~/ndsp-presets/tools/loudar --models ~/ndsp-presets/tools/codec-models \\
        --out ~/ndsp-presets/handover/<date>/loudar-gate.json       # unit 0: the reproduction gate, before our audio

Per clip (a search half of 216,000 samples at 48 kHz): LOUDAR's level rule in (`loudar_gain`), zero-padded to
`pad_len`, `y = diff_params.transform_fwd(x)`; `torch.manual_seed(operator seed)` and the operator built;
`torch.manual_seed(run seed)` and `sampler.predict(y=y, operator=op, reference=y, device=cpu)`;
`torch.manual_seed(decode seed)` and `diff_params.transform_bwd(x_est)`; cut to the clip; the gain undone.

No file is loaded with `weights_only=False`: the checkpoint's pickle globals are listed by `pickletools` (nothing is
executed), it loads with `weights_only=True` inside `torch.serialization.safe_globals` naming only the omegaconf
classes it holds, and any other global stops the run (to the user). `TORCH_FORCE_WEIGHTS_ONLY_LOAD=1`,
`WANDB_MODE=disabled`, `ENABLE_TORCH_COMPILE=0`, `HF_HOME=<--models>/hf` and `HF_HUB_OFFLINE=1` are set before
anything is imported.
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
CLIP = 216000                     # a search half: 4.5 s (pretrain_set.HALVES)
LD_SEED = 20261701                # above every seed on main (the codec row's RT_SEED is the highest)
M2L_HOP, M2L_EXTRA = 4096, 1536
LOUDAR_RMS_DB, LOUDAR_SEG_S, LOUDAR_HOP_S, LOUDAR_FLOOR = -18.0, 0.4, 0.1, 1e-8
THREADS = 4
LOUDAR_COMMIT = "9f3bd1659991b584afcfa7a3ac395c0512f24237"
LOUDAR_REPO = "msvento/loudar"    # Hugging Face, MIT tag, not gated
LOUDAR_REVISION = "6de0a99b"      # the plan's; unit 0 fetches "main", checks it is this, records the full sha
CHECKPOINT = "GuitarFx-175000.pt"
CHECKPOINT_SHA256 = "d86e08bbb94bb12cef0b907dd7f3fd67ba112cc463c8ee0e964855155985c297"
CHECKPOINT_SIZE = 1083089737
TESTER_YAML = "conf/tester/blind_estimation_m2l_EDM_guitar.yaml"
NETWORK_YAML = "conf/network/dit_M2L.yaml"
DIFF_YAML = "conf/diff_params/FM_to_EDM_m2l.yaml"
SETTINGS = ("released", "paper")
RELEASED_FIT = {"operator_updates_per_step": 1, "lr": 1e-3, "weight_decay": 0.1}
PAPER_FIT = {"operator_updates_per_step": 10, "lr": 1e-4, "weight_decay": 1.0}   # arXiv 2608.01972, section 3.1
SHARED = {"T": 300, "order": 1, "Schurn": 20, "zeta": 0.3}                       # the YAML's and the paper's
CONFIG_MODULES = ("omegaconf",)    # the only globals added to weights_only's allowlist
TORCH_SAFE = ("torch.", "collections.OrderedDict", "builtins.", "_codecs.encode")   # weights_only's own allowlist
STRING_OPS = ("SHORT_BINUNICODE", "BINUNICODE", "UNICODE", "BINUNICODE8", "SHORT_BINSTRING", "BINSTRING", "STRING")
GATE_EXAMPLES = 6
GATE_KINDS = ("distorted", "original", "LOUDAR")
DEMO_DIR = "docs/static/audio_examples/guitar_distortion_removal"   # the authors' published guitar examples
GATE_TOL_DB = 1.0                 # reproduction and length: within 1.0 dB (mean floored log-mel distance)
GATE_SETTING_TIE_DB = 0.1         # within this the released setting is kept
GATE_DIRECTION_MIN = 5            # our output closer to the original than the input on at least 5 of 6
COST_STOP_H = 8.0                 # wall hours at 4 threads: the gate's 18 runs and the 23 deciding clips
CHECK_RUNS = {"full": 1, "cut": 3}  # the timed whole and cut clip, the seeded rerun, the zeros-reference run
DECIDING_CLIPS = 23
GOAT_CLIPS = 24
ENV = {"TORCH_FORCE_WEIGHTS_ONLY_LOAD": "1", "WANDB_MODE": "disabled", "ENABLE_TORCH_COMPILE": "0",
       "HF_HUB_OFFLINE": "1"}


# --- the pure rules ------------------------------------------------------------------------------------------------------

def pad_len(n):
    """(Pure.) The least 4,096 k + 1,536 at or above n (218,624 for 216,000); equal to `codec_roundtrip.pad_len`."""
    if n <= M2L_EXTRA:
        return M2L_EXTRA
    return M2L_HOP * math.ceil((n - M2L_EXTRA) / M2L_HOP) + M2L_EXTRA


def seeds(slot, j):
    """(Pure.) A clip's three seeds: the operator's (set before the operator is built), the run's (before `predict`)
    and the decode's (before `transform_bwd`). slot 0 is `ld-stem`/`ld-rec`, 1 is `ld-stem-b`; j the part's index in
    sorted keys."""
    base = LD_SEED + 1000 * slot + j
    return {"operator": base + 250, "run": base, "decode": base + 500}


def tester_args(setting):
    """(Pure.) The tester's settings as a plain dict: `released` is the YAML's values; `paper` changes exactly the
    operator's fit (updates a step, learning rate, weight decay) to the paper's. wandb off; seeded per clip."""
    if setting not in SETTINGS:
        raise SystemExit(f"--setting {setting!r}: one of {SETTINGS}")
    fit = RELEASED_FIT if setting == "released" else PAPER_FIT
    return {"sampling_params": {"T": SHARED["T"], "order": SHARED["order"], "Schurn": SHARED["Schurn"]},
            "dps_params": {"zeta": SHARED["zeta"], "normalize_std_from_reference": False},
            "opt_latent_params": {"operator_updates_per_step": fit["operator_updates_per_step"],
                                  "optimizer_operator": {"lr": fit["lr"], "weight_decay": fit["weight_decay"]}},
            "wandb": {"use": False}}


def flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def input_refusal(rec, key, sha, n, finite=True):
    """(Pure.) Why a clip may not go to LOUDAR, or None: in.json's sha256, CLIP samples, all finite."""
    ent = ((rec or {}).get("parts") or {}).get(key)
    if not isinstance(ent, dict) or ent.get("sha256") != sha:
        return f"{key}: not the file in.json names"
    if n != CLIP:
        return f"{key}: {n} samples, not {CLIP}"
    if not finite:
        return f"{key}: a non-finite sample"
    return None


def keys_for(keys, sets):
    """(Pure.) The part keys of the named sets (keys start with the set's name and '__'), sorted."""
    return sorted(k for k in keys if k.split("__", 1)[0] in sets)


def globals_refusal(found):
    """(Pure.) The checkpoint's pickle globals ["module.name"] -> (the config classes to allow, why it refuses or
    None). Torch's tensor globals and builtins are weights_only's own; the omegaconf classes are added to
    `safe_globals`; any other global stops (to the user)."""
    allow, other = [], []
    for g in sorted(set(found)):
        if g.startswith(TORCH_SAFE):
            continue
        if g.split(".", 1)[0] in CONFIG_MODULES:
            allow.append(g)
        else:
            other.append(g)
    return allow, (f"the checkpoint pickles {other}: not a torch or config class; stop and ask" if other else None)


def gate_seconds(full_s, cut_s):
    """(Pure.) The gate's projected seconds: its 18 runs (6 examples x 2 settings whole, 6 cut) and the 4 timing and
    check runs (the timed whole and cut clip, the seeded rerun, the zeros-reference run), counted in full even where a
    run is reused."""
    return (2 * GATE_EXAMPLES + CHECK_RUNS["full"]) * full_s + (GATE_EXAMPLES + CHECK_RUNS["cut"]) * cut_s


def cost_fit(gate_s, clip_s, budget_h=COST_STOP_H):
    """(Pure.) The cost stop, in wall hours at 4 threads. gate_s: the gate's seconds (`gate_seconds`: its 18 runs and
    the 4 timing and check runs); clip_s: seconds a 4.5-s clip. The gate and the 23 deciding clips must fit, or stop
    and ask; GOAT's 24 clips, then `ld-stem-b`'s 23, are added in that order only while the total stays under the
    budget."""
    total = gate_s + DECIDING_CLIPS * clip_s
    out = {"fits": total <= budget_h * 3600, "goat": False, "ld_stem_b": False}
    if out["fits"] and total + GOAT_CLIPS * clip_s <= budget_h * 3600:
        total += GOAT_CLIPS * clip_s
        out["goat"] = True
        if total + DECIDING_CLIPS * clip_s <= budget_h * 3600:
            total += DECIDING_CLIPS * clip_s
            out["ld_stem_b"] = True
    out["total_h"] = total / 3600
    out["window_10s_s"] = clip_s * 10 / 4.5          # beside: what one 10-s song window would cost (linear guess)
    return out


def gate_reading(d):
    """(Pure.) The reproduction gate from floored log-mel distances to the original, per example (6 each).
    d: {"distorted": [..], "authors": [..], "ours": {setting: [..]}, "cut": [..] (ours cut to 4.5 s, chosen setting),
    "from_full": [..] (the same 4.5 s taken from our full run)}. The setting is the lower mean (within 0.1 dB the
    released); direction: ours closer than the distorted input on at least 5 of 6; reproduction: |mean ours - mean
    authors| <= 1.0 dB; length: mean cut - mean from-full <= 1.0 dB. The tolerance is also given as a fraction of the
    authors' own gain (mean distorted - mean authors). -> the reading."""
    def mean(v):
        return sum(v) / len(v)
    ours = {s: v for s, v in d["ours"].items() if v}
    if not ours:
        raise SystemExit("gate_reading needs at least one setting's six distances")
    m = {s: mean(v) for s, v in ours.items()}
    setting = "released" if "released" in m and all(m["released"] - m[s] <= GATE_SETTING_TIE_DB for s in m) \
        else min(m, key=m.get)
    gain = mean(d["distorted"]) - mean(d["authors"])
    out = {"setting": setting, "mean_d": m, "mean_distorted": mean(d["distorted"]),
           "mean_authors": mean(d["authors"]), "authors_gain_db": gain,
           "tolerance_fraction_of_gain": (GATE_TOL_DB / gain) if gain > 0 else None,
           "direction": sum(o < x for o, x in zip(ours[setting], d["distorted"])),
           "reproduction_db": m[setting] - mean(d["authors"])}
    out["direction_ok"] = out["direction"] >= GATE_DIRECTION_MIN
    out["reproduction_ok"] = abs(out["reproduction_db"]) <= GATE_TOL_DB
    if d.get("cut") and d.get("from_full"):
        out["length_db"] = mean(d["cut"]) - mean(d["from_full"])
        out["length_ok"] = out["length_db"] <= GATE_TOL_DB
    else:
        out["length_db"], out["length_ok"] = None, None
    out["passed"] = bool(out["direction_ok"] and out["reproduction_ok"] and out["length_ok"])
    return out


# --- numpy ---------------------------------------------------------------------------------------------------------------

def loudar_gain(x, sr=SR):
    """A copy of `codec_roundtrip.loudar_gain` (a test holds the two equal): the loudest 400-ms frame (hop 100 ms,
    `unfold` with the tail dropped, RMS floored at 1e-8) to -18 dB; 10 ** (gain / 20 + 1e-6)."""
    import numpy as np

    seg, hop = int(sr * LOUDAR_SEG_S), int(sr * LOUDAR_HOP_S)
    x = np.asarray(x, np.float64)
    if len(x) < seg:
        raise ValueError(f"{len(x)} samples: shorter than one {seg}-sample frame")
    n = (len(x) - seg) // hop + 1
    frames = np.lib.stride_tricks.sliding_window_view(x, seg)[::hop][:n]
    rms = np.sqrt((frames ** 2).mean(axis=1))
    return float(10 ** ((LOUDAR_RMS_DB - 20 * np.log10(np.maximum(rms, LOUDAR_FLOOR)).max()) / 20 + 1e-6))


def logmel(x, n_fft, sr=SR, n_mels=80, fmin=80.0, fmax=10000.0):
    """A copy of `scratch_codec.logmel` (a test holds the two equal)."""
    import numpy as np

    hop = n_fft // 4
    w = np.hanning(n_fft)
    n = 1 + (len(x) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n)[:, None]
    pw = np.abs(np.fft.rfft(x[idx] * w, axis=1)) ** 2
    f = np.fft.rfftfreq(n_fft, 1 / sr)

    def mel(h):
        return 2595 * np.log10(1 + h / 700)
    edges = 700 * (10 ** (np.linspace(mel(fmin), mel(fmax), n_mels + 2) / 2595) - 1)
    fb = np.zeros((n_mels, len(f)))
    for i in range(n_mels):
        a, b, c = edges[i:i + 3]
        fb[i] = np.clip(np.minimum((f - a) / (b - a), (c - f) / (c - b)), 0, None)
    return 10 * np.log10(pw @ fb.T + 1e-20)


def floored(a, b, floor_db=50.0):
    """A copy of `scratch_codec.floored`."""
    import numpy as np

    fl = a.max() - floor_db
    a2, b2 = np.maximum(a, fl), np.maximum(b, fl)
    keep = (a > fl) | (b > fl)
    d = b2 - a2
    d = d - d[keep].mean()
    return float(np.abs(d[keep]).mean())


def gate_d(original, y):
    """The gate's distance: the mean of the floored log-mel distances at 256 and 2,048 samples."""
    import numpy as np

    n = min(len(original), len(y))
    o, z = np.asarray(original[:n], np.float64), np.asarray(y[:n], np.float64)
    return (floored(logmel(o, 256), logmel(z, 256)) + floored(logmel(o, 2048), logmel(z, 2048))) / 2


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --- LOUDAR (torch inside) ------------------------------------------------------------------------------------------------

def set_env(models):
    """The environment, before anything is imported: weights-only loads, wandb off, no torch.compile, the codec
    models' Hugging Face cache offline."""
    if os.environ.get("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "0").lower() in ("1", "y", "yes", "true"):
        raise SystemExit("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD is set: no file is loaded with weights_only=False")
    hf = pathlib.Path(models).expanduser() / "hf"
    if os.environ.get("HF_HOME") and pathlib.Path(os.environ["HF_HOME"]).expanduser().resolve() != hf.resolve():
        raise SystemExit(f"HF_HOME is {os.environ['HF_HOME']}, not {hf}: unset it")
    if not hf.is_dir():
        raise SystemExit(f"no Hugging Face cache at {hf}")
    os.environ.update(ENV)
    os.environ["HF_HOME"] = str(hf)


def pickle_globals(path):
    """The globals a torch zip checkpoint's pickle names, listed by `pickletools` (nothing is unpickled or run)."""
    import pickletools
    import zipfile

    found = set()
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith("data.pkl")]
        if len(names) != 1:
            raise SystemExit(f"{path}: {len(names)} data.pkl entries, not 1")
        data = z.read(names[0])
    pushed, memo = [], {}          # what each opcode pushed (strings kept, anything else None) and the memo
    for op, arg, _ in pickletools.genops(data):
        if op.name in STRING_OPS:
            pushed.append(arg)
        elif op.name in ("BINGET", "LONG_BINGET", "GET"):
            pushed.append(memo.get(int(arg)))
        elif op.name == "MEMOIZE":
            memo[len(memo)] = pushed[-1] if pushed else None
        elif op.name in ("BINPUT", "LONG_BINPUT", "PUT"):
            memo[int(arg)] = pushed[-1] if pushed else None
        elif op.name == "GLOBAL":
            found.add(arg.replace(" ", ".", 1))
            pushed.append(None)
        elif op.name == "STACK_GLOBAL":
            mod, name = (pushed[-2], pushed[-1]) if len(pushed) >= 2 else (None, None)
            if not isinstance(mod, str) or not isinstance(name, str):
                raise SystemExit(f"{path}: a STACK_GLOBAL whose names cannot be read: stop and ask")
            found.add(f"{mod}.{name}")
            pushed.append(None)
        else:
            pushed.append(None)
    return sorted(found)


def load_checkpoint(path, manifest):
    """The checkpoint's EMA weights: its size and sha256 the declared (and the manifest's), its pickle globals listed
    first, then `torch.load(weights_only=True)` inside `safe_globals` of only its omegaconf classes."""
    import importlib

    import torch

    p = pathlib.Path(path)
    sha = file_sha(p)
    if sha != CHECKPOINT_SHA256 or p.stat().st_size != CHECKPOINT_SIZE:
        raise SystemExit(f"{p.name}: sha256 {sha[:12]} or size is not the declared")
    ent = ((manifest or {}).get("files") or {}).get(f"loudar/{CHECKPOINT}") or {}
    if ent.get("sha256") != sha:
        raise SystemExit(f"{p.name}: not the manifest's")
    found = pickle_globals(p)
    allow, why = globals_refusal(found)
    if why:
        raise SystemExit(why)
    objs = []
    for g in allow:
        mod, name = g.rsplit(".", 1)
        objs.append(getattr(importlib.import_module(mod), name))
    with torch.serialization.safe_globals(objs):
        state = torch.load(str(p), map_location="cpu", weights_only=True)
    return state["ema"], {"sha256": sha, "globals": found, "allowed": allow}


def build(code, models, setting, manifest):
    """LOUDAR's network (DiT, the checkpoint's EMA weights), the `m2l` parameterisation and the DPS-EM sampler, from
    its own YAML files with `tester_args(setting)` applied; CPU, THREADS threads."""
    import sys

    set_env(models)
    import torch

    torch.set_num_threads(THREADS)
    src = pathlib.Path(code).expanduser() / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import hydra
    from omegaconf import OmegaConf

    tester = OmegaConf.load(src / TESTER_YAML)
    over = OmegaConf.create(tester_args(setting))
    tester = OmegaConf.merge(tester, over)
    args = OmegaConf.create({"tester": tester, "network": OmegaConf.load(src / NETWORK_YAML),
                             "diff_params": OmegaConf.load(src / DIFF_YAML), "exp": {"sample_rate": SR}})
    diff_params = hydra.utils.instantiate(args.diff_params)
    network = hydra.utils.instantiate(args.network)
    from huggingface_hub import hf_hub_download

    ema, ck = load_checkpoint(hf_hub_download(repo_id=LOUDAR_REPO, filename=CHECKPOINT, local_files_only=True),
                              manifest)      # the cache's main ref (fetched by revision "main"); the sha256 pins it
    network.load_state_dict(ema)
    network = network.to("cpu").eval()
    sampler = hydra.utils.instantiate(args.tester.sampler, network, diff_params, args)
    used = {f: file_sha(src / f) for f in (TESTER_YAML, NETWORK_YAML, DIFF_YAML, "testing/DPS_EM.py",
                                           "testing/operators/latent_models.py", "diff_params/diffusion_latent.py",
                                           "networks/dit.py", "networks/transformer.py")}
    return {"torch": torch, "hydra": hydra, "args": args, "diff_params": diff_params, "sampler": sampler,
            "checkpoint": ck, "code_sha256": used}


def run_clip(m, x, sd, zero_reference=False):
    """One clip through LOUDAR: the gain, the padding, the latent, the seeded operator and run, the seeded decode, the
    cut, the gain undone. `reference` is y (LOUDAR only logs it, with wandb off); `zero_reference` passes zeros, the
    gate's check that it changes nothing. -> (float32 clip, the final operator loss)."""
    import numpy as np

    torch, hydra = m["torch"], m["hydra"]
    x = np.asarray(x, np.float64)
    g = loudar_gain(x)
    xin = np.pad(x * g, (0, pad_len(len(x)) - len(x)))
    with torch.no_grad():
        y = m["diff_params"].transform_fwd(torch.tensor(xin, dtype=torch.float32)[None])
    torch.manual_seed(sd["operator"])
    op = hydra.utils.instantiate(m["args"].tester.op_model).to("cpu")
    torch.manual_seed(sd["run"])
    ref = torch.zeros_like(y) if zero_reference else y.detach()
    x_est, op = m["sampler"].predict(y=y.detach(), operator=op, reference=ref, device=torch.device("cpu"))
    torch.manual_seed(sd["decode"])
    with torch.no_grad():
        out = m["diff_params"].transform_bwd(x_est)
    out = out.detach().cpu().numpy().reshape(-1).astype(np.float64)
    if len(out) < len(x):
        raise SystemExit(f"LOUDAR returned {len(out)} samples, fewer than {len(x)}")
    loss = getattr(m["sampler"], "rec_loss_after", None)
    return np.asarray(out[:len(x)] / g, np.float32), loss


def versions():
    from importlib import metadata

    out = {}
    for p in ("torch", "numpy", "linear-cae", "hydra-core", "omegaconf", "einops", "wandb"):
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = None
    return out


def cmd_run(a):
    """LOUDAR on every clip of the named sets in --inp (in.json's), written once to --out with run-<tag>.json."""
    import numpy as np

    inp, out = pathlib.Path(a.inp).expanduser(), pathlib.Path(a.out).expanduser()
    tag = "-".join(sorted(a.sets))
    rec_p = out / f"run-{out.name}-{tag}.json"
    if rec_p.exists():
        raise SystemExit(f"{rec_p} exists: never overwritten")
    in_rec = json.loads((inp.parent / "in.json").read_text())["names"][inp.name]
    keys = keys_for(in_rec["parts"], a.sets)
    all_keys = sorted(in_rec["parts"])
    for k in keys:
        if (out / f"{k}.npy").exists():
            raise SystemExit(f"{out / k}.npy exists: never overwritten")
    manifest = json.loads((pathlib.Path(a.models).expanduser() / "manifest.json").read_text())
    m = build(a.code, a.models, a.setting, manifest)
    out.mkdir(parents=True, exist_ok=True)
    secs, parts = [], {}
    for k in keys:
        f = inp / f"{k}.npy"
        x = np.load(f)
        why = input_refusal({"parts": in_rec["parts"]}, k, file_sha(f), len(x), bool(np.isfinite(x).all()))
        if why:
            raise SystemExit(why)
        sd = seeds(a.seed_slot, all_keys.index(k))
        t0 = time.time()
        y, loss = run_clip(m, x, sd)
        secs.append(time.time() - t0)
        if not np.isfinite(y).all():
            raise SystemExit(f"{k}: a non-finite output")
        np.save(out / f"{k}.npy", y)
        parts[k] = {"sha256": file_sha(out / f"{k}.npy"), "seeds": sd, "seconds": secs[-1], "operator_loss": loss}
        print(f"{len(parts)}/{len(keys)} {k[-50:]}: {secs[-1]:.0f} s", flush=True)
    rec_p.write_text(json.dumps({"plan": "docs/scratch-search-plan.md section 13", "setting": a.setting,
                                 "tester": tester_args(a.setting), "seed_slot": a.seed_slot, "sets": a.sets,
                                 "commit": LOUDAR_COMMIT, "code_sha256": m["code_sha256"],
                                 "checkpoint": m["checkpoint"], "versions": versions(), "threads": THREADS,
                                 "device": "cpu", "env": {k: os.environ.get(k) for k in ENV},
                                 "seconds_a_clip": sum(secs) / len(secs) if secs else None, "parts": parts,
                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"LOUDAR RUN DONE {out.name} {tag}: {len(parts)} clips, {sum(secs) / max(1, len(secs)):.0f} s a clip")


def cmd_gate(a):
    """Unit 0, before any of our audio: the gate's reference distances from the authors' files (zero runs); one clip
    timed whole and cut (released) and the cost stop; a second seeded run and a zeros-reference run byte-equal; the six
    examples with both settings and the setting chosen; then the six cut to 4.5 s with that setting, against the same
    4.5 s of its full runs. 18 runs in all. -> --out (loudar-gate.json)."""
    import numpy as np
    import soundfile as sf

    code = pathlib.Path(a.code).expanduser()
    demo = code / DEMO_DIR
    outp = pathlib.Path(a.out).expanduser()
    if outp.exists():
        raise SystemExit(f"{outp} exists: never overwritten")

    def load(kind, i):
        x, sr = sf.read(str(demo / f"{kind}_{i}.wav"), dtype="float32", always_2d=True)
        if sr != SR:
            raise SystemExit(f"{kind}_{i}: {sr} Hz, not {SR}")
        return x.mean(axis=1)

    def stop(res, why):
        outp.write_text(json.dumps(dict(res, stopped=why), indent=1))
        raise SystemExit(f"{why}: stop and ask")
    ex = [{k: load(k, i) for k in GATE_KINDS} for i in range(GATE_EXAMPLES)]
    d = {"distorted": [gate_d(e["original"], e["distorted"]) for e in ex],
         "authors": [gate_d(e["original"], e["LOUDAR"]) for e in ex], "ours": {}}
    res = {"plan": "docs/scratch-search-plan.md section 13 (unit 0)", "reference_zero_runs": json.loads(json.dumps(d)),
           "demo_sha256": {f"{k}_{i}": file_sha(demo / f"{k}_{i}.wav") for i in range(GATE_EXAMPLES)
                           for k in GATE_KINDS}}
    manifest = json.loads((pathlib.Path(a.models).expanduser() / "manifest.json").read_text())
    built = {"released": build(a.code, a.models, "released", manifest)}
    m = built["released"]
    x0 = ex[0]["distorted"]
    t0 = time.time()
    y_full0, _ = run_clip(m, x0, seeds(0, 0))
    full_s = time.time() - t0
    t0 = time.time()
    y_cut0, _ = run_clip(m, x0[:CLIP], seeds(0, 0))
    cut_s = time.time() - t0
    cost = cost_fit(gate_seconds(full_s, cut_s), cut_s)
    res["timing"] = {"full_s": full_s, "cut_s": cut_s, "full_n": len(x0), "cost": cost}
    if not cost["fits"]:
        stop(res, "the cost stop: the gate and the 23 deciding clips do not fit 8 wall hours at 4 threads")
    y_rep, _ = run_clip(m, x0[:CLIP], seeds(0, 0))
    y_zero, _ = run_clip(m, x0[:CLIP], seeds(0, 0), zero_reference=True)
    res["repeat_byte_equal"] = bool(np.array_equal(y_cut0, y_rep))
    res["zeros_reference_byte_equal"] = bool(np.array_equal(y_cut0, y_zero))
    if not (res["repeat_byte_equal"] and res["zeros_reference_byte_equal"]):
        stop(res, "a seeded rerun or the zeros-reference run is not byte-equal")
    outs = {}
    for s in SETTINGS:
        if s not in built:
            built[s] = build(a.code, a.models, s, manifest)
        outs[s] = [y_full0 if (s == "released" and i == 0) else run_clip(built[s], e["distorted"], seeds(0, i))[0]
                   for i, e in enumerate(ex)]
        d["ours"][s] = [gate_d(e["original"], y) for e, y in zip(ex, outs[s])]
    chosen = gate_reading(json.loads(json.dumps(d)))["setting"]
    d["cut"], d["from_full"] = [], []
    for i, e in enumerate(ex):
        y_c = y_cut0 if (chosen == "released" and i == 0) else run_clip(built[chosen], e["distorted"][:CLIP],
                                                                         seeds(0, i))[0]
        d["cut"].append(gate_d(e["original"][:CLIP], y_c))
        d["from_full"].append(gate_d(e["original"][:CLIP], outs[chosen][i][:CLIP]))
    res.update(distances=d, reading=gate_reading(d), versions=versions(), checkpoint=m["checkpoint"],
               code_sha256=m["code_sha256"], time=time.strftime("%Y-%m-%d %H:%M:%S"))
    outp.write_text(json.dumps(res, indent=1))
    print(f"LOUDAR GATE {'PASS' if res['reading']['passed'] else 'STOP (ask)'}: {json.dumps(res['reading'])}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--inp", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--sets", nargs="+", required=True, choices=("bks", "panel", "goat"))
    r.add_argument("--setting", required=True, choices=SETTINGS)
    r.add_argument("--seed-slot", type=int, choices=(0, 1), default=0)
    r.add_argument("--models", required=True)
    r.add_argument("--code", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--code", required=True)
    g.add_argument("--models", required=True)
    g.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    (cmd_run if a.cmd == "run" else cmd_gate)(a)


if __name__ == "__main__":
    main()
