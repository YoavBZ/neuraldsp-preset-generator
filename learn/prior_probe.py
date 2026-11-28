"""The LOUDAR prior timing probe (`docs/prior-probe-plan.md`; ledger `preset-ladder` `phase_scratch_prior_probe`, later
`phase_scratch_prior_probe_outcome`): what route 3's fine-tune of LOUDAR's DI prior would cost on this Mac. Steps per
second on MPS at the real segment length (526,080 samples, batch 2), memory, and whether MPS gradients can be trusted
on LOUDAR's training path. Zero renders; no model is ever written.

    $MAIN -m learn.prior_probe hours [--dry]           # trusted DI hours per source, from stored inventories
    $MAIN -m learn.prior_probe prep [--dry]            # the 16 GOAT DI segments (about 34 MB) -> PF/fs/prior-probe/
    $LV learn/prior_probe.py check --code ~/ndsp-presets/tools/loudar --models ~/ndsp-presets/tools/codec-models
    $LV learn/prior_probe.py time --steps 200          # MPS; writes only time-<stamp>.json
    $MAIN -m learn.prior_probe read                    # the PP code, the projections, memory, the tables, the hours

**LOUDAR's own code runs** (the review's amendment 1, option 1). `Trainer.train_step` and `Trainer.update_ema` are
called unbound on a stub object holding exactly the attributes they read (`args`, `network`, `diff_params`,
`optimizer`, `ema`, `it`, `dset`, `device`, and `get_batch` bound from `Trainer.get_batch`), in `training_loop`'s order:
`train_step`, `update_ema`, `it += 1`. No LOUDAR file is edited. `logging.log` and `log_spectrograms` are False. Two of
LOUDAR's own modules that `training/trainer.py` imports but these methods never use (`utils.log`, `utils.training_utils`)
are placeholder modules during the import, because pandas, plotly and torchaudio are not in the venv and nothing is
downloaded; a placeholder raises on any use. The training `diff_params` is `conf/diff_params/FM_m2l.yaml` (class FM),
not the tester's `FM_to_EDM_wrapper`; the network is `config_train_GuitarFx.yaml`'s default `dit_M2L`; the optimizer,
batch, length, clip and EMA are `conf/exp/GuitarFx.yaml`'s. Every source file and function used is pinned by sha256
(`LOUDAR_FILES`, `LOUDAR_FUNCS`); a pin that fails is PP-anomaly. The segments are RMS-normalised to -18 dB by LOUDAR's
own `utils.normalization.apply_RMS_normalization(..., use_gate=True)`, as `GuitarFxIterable` does.

**Observers, never changing a value.** The FM instance's `loss_fn`, `sample_time_training` and `sample_prior` are
wrapped on the instance (each calls the class's own method and keeps a copy of what it returns), and
`torch.nn.utils.clip_grad_norm_` is wrapped for the run (it keeps the gradients before and after and the returned
norm, and applies a declared fallback when one is in use). t and the noise are drawn on the CPU by LOUDAR's code, so
one seed gives both devices the same draws (checked).

**The check** (`check`, CPU at 4 threads and MPS; the review's amendment 2): one fixed batch, one seed.
- The encoder forward: MPS latents against the CPU's, relative L2 at most 1e-3. This check alone judges the encoder
  (and so its CPU fallback).
- Run 1, the network alone on shared CPU latents; run 2, end to end: the MPS step with the chosen encoder against the
  CPU network fed that MPS run's own latents. Each compares the loss (1e-4 relative), every gradient before the clip
  per tensor and globally (1e-3 relative L2, a tensor's norm floored at 1% of the RMS tensor norm), the clip's
  returned norm (1e-3), its non-finite count (0) and the gradients after it (1e-3), and records whether the clip
  scaled (norm above 1).
- A figure that misses its tolerance passes only if its error against a CPU float64 reference is within 3 times CPU
  float32's own error against that reference (the calibration). The float64 reference runs LOUDAR's `FM.loss_fn` on a
  float64 copy of the network with the same t, noise and the run's shared latents (the rotary frequency buffer stays
  float32, as LOUDAR computes rotary angles in float32); if it cannot run, nothing is calibrated. A calibrated pass is
  allowed only when the reference itself holds (CPU float32 against float64 within the direct tolerances on the loss
  and the global gradient, and the same draws on both devices), and never for a tensor whose CPU error against
  float64 is above 0.1; otherwise only the direct checks apply, and the record says so.
- AdamW's step and the EMA update are compared from identical gradients and weights copied to both devices (the EMA
  on both of its branches, `it` 1 and 175,000).
- Five steps on each device from the same start: the loss sequence, the clip norms and the weight change, reported;
  the CPU rate is quoted from steps 2 to 5.
- Fallbacks, each checked the same way: the encoder on the CPU (when its latent check fails); the clip with
  `foreach=False`, then the clip norm on the CPU. An unsupported op in the encoder or the clip tries its fallback; an unsupported op anywhere else, or MPS out of
  memory, is PP-cpu-only with the op or the memory named. Any other error stops the probe (to the orchestrator).

**The timing** (`time`, MPS, the configuration the check passed, fallbacks included): 200 steps, `torch.mps.synchronize()`
before each clock read; steps 1-20 are warm-up, steps 21-200 give the rate. The encode share comes from a separate
encode-only block (50 encodes, 5 warm-up), never from a sync inside the step. Beside it, 100 steps (20 warm-up) at
218,624 samples (our 216,000-sample clip padded as LOUDAR pads it). Data are in memory before the clock. A step is
non-finite when its loss, the clip's returned norm, or any parameter at its end is not finite. Peak RSS and MPS
driver memory are recorded. The rate excludes LOUDAR's in-step resample, which is right for 48 kHz data.

**Idle** (amendment 6): at the start and end of each timed block, no render process (`pgrep -f au_render_server`) and
no other torch or MPS process (`pgrep -f` on the tools' venvs and the training commands), the probe's own process and
its parents left out; the counts are recorded. `check` and `time` refuse while another torch or MPS process runs (never
two MPS jobs); `check` also refuses beside renders (it competes for the CPU's performance cores). A timed block that
was not idle at both ends is labelled; the quoted rate comes only from an idle 526,080-sample block, so `read` refuses
until one exists (rerun `time` when the machine is idle).

**The code** (`pp_code`, the first that holds, in this order): PP-anomaly (a pin or hash fails, a file outside the
list is read, or a weights file is written), PP-cpu-only, PP-unstable (the checks hold but a non-finite step appears),
PP-mps-fallback (the checks hold only with a declared fallback; the fine-tune must use it), PP-mps (every check holds on
LOUDAR's own path and 200 finite steps). One code, then stop: no model is kept, and the fine-tune needs its own
declaration and go.

**`hours`** (amendment 4) counts trusted DI hours per source from stored inventories only (zero renders; it reads no
audio but EGFxSet's WAV headers): the clean-DI library's trusted sections (training_ok, clean, disjoint, split
library) less, in order, Silent Waves and Drowning, the held bands (V-real, NS, the panel, BKS, the reserve:
`capture_labels.HELD_BANDS`), what `clean_di.refuse_held_out` refuses, the reserve's stage-F DIs, the DIs the user
marked too low or metal-style (the DI-scope page's drops and batch 3's marks), the hum-audit superset and the 47 draw
sections; EGDB's and EGFxSet's DIs as stored, unscreened; GOAT apart, as the prior's own training data, never checked
for scope, less item_5 and the drawn items. It is a count only; the fine-tune declares its own set.

**Public repo:** git gets 12-hex tags (`tag`) only; item ids, part keys and paths stay under `PF/fs/prior-probe/`.

The pure parts (the codes, the tolerances and checks, the projections, the segment rule, the idle rule, the hours
tally, the guards) are tested in tests/test_prior_probe.py with no numpy or torch at import; this module's top-level
imports are the standard library and `loudar_run` (stdlib-only at its top), so `$LV learn/prior_probe.py` runs as a
script.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import pathlib
import random
import re
import subprocess
import sys
import time

try:
    from learn import loudar_run as LR
except ImportError:                    # run as a script ($LV learn/prior_probe.py): learn/ is sys.path[0]
    import loudar_run as LR

REPO = pathlib.Path(__file__).resolve().parents[1]
LEDGER = REPO / "docs" / "dev-test-ledger.json"
LEDGER_ID = "preset-ladder"
KEY = "phase_scratch_prior_probe"      # the declaration; later KEY + "_outcome"
PLAN = "docs/prior-probe-plan.md"
DATA = pathlib.Path("~/ndsp-presets").expanduser()
PF_SUB = "learn/trusted-data/pipeline-fix"
OUT_SUB = "fs/prior-probe"             # PF/fs/prior-probe/: segments/, hours.json, prep.json, check.json, time-*.json
CODE_DEFAULT = "~/ndsp-presets/tools/loudar"
MODELS_DEFAULT = "~/ndsp-presets/tools/codec-models"

SR = 48000
SEG = 526080                           # conf/exp/GuitarFx.yaml audio_len (10.96 s)
SEG_SHORT = LR.pad_len(LR.CLIP)        # 218,624: our 216,000-sample clip padded as LOUDAR pads it
BATCH = 2                              # conf/exp/GuitarFx.yaml batch_size
N_SEGMENTS = 16                        # GOAT DI segments, cycled
SEED = 20261801                        # above every seed on main (LOUDAR's runs use 20261701)
CHECK_SEED = SEED + 100                # the check's one fixed batch: t and the noise
FIVE_SEED = SEED + 200                 # the five steps (one seed a step: FIVE_SEED + k)
TIME_SEED = SEED + 300                 # each timed block (seeded once, as Trainer.__init__ seeds once)
RMS_DB = -18.0                         # conf/dset/GuitarFx.yaml rms_normalize, use_gate True
STEPS, WARMUP = 200, 20
SHORT_STEPS, SHORT_WARMUP = 100, 20
ENCODE_BLOCK, ENCODE_WARMUP = 50, 5
FIVE = 5
CPU_RATE_STEPS = (2, 5)                # the CPU rate: steps 2 to 5 of the five (1-based)
RELEASED_STEPS = 175000                # the released checkpoint's count (GuitarFx-175000.pt); no target is chosen here
THREADS = 4
EMA_ITS = (1, 175000)                  # the EMA check: the ramp-up branch and the rate branch
TIMED_IT0 = 0                          # timed steps start at it = 0, as training_loop sets it

TOL = {"encoder": 1e-3, "loss": 1e-4, "grad": 1e-3, "clip_norm": 1e-3, "clip_after": 1e-3, "adamw": 1e-3,
       "ema": 1e-3}                    # relative; they catch a broken op (the known fault was 81-100% off), decide no route
CALIB_MULT = 3.0                       # a miss passes only within 3x CPU float32's own error against float64
CALIB_CAP = 0.1                        # no tensor is calibrated whose CPU float32 error against float64 is above this
PER_TENSOR_FLOOR = 0.01                # a tensor's norm floored at 1% of the RMS tensor norm (near-zero tensors)
MAX_NORM = 1.0                         # conf/exp/GuitarFx.yaml max_grad_norm
RATE_NOTE = ("the rate excludes LOUDAR's in-step resample (get_batch's resample_batch, which GOAT's 44.1-kHz files "
             "take in LOUDAR's own training), which is right for 48 kHz data")

CODES = ("PP-anomaly", "PP-cpu-only", "PP-unstable", "PP-mps-fallback", "PP-mps")   # the order: first that holds
PP_TABLE = {
    "PP-anomaly": "a pin or hash fails, a file outside the list is read, or a weights file is written",
    "PP-cpu-only": ("MPS gradients do not match even with the declared fallbacks, or an unsupported op outside the "
                    "encoder and the clip, or MPS out of memory (the op or the memory named); the CPU rate is quoted "
                    "from steps 2 to 5 of the five"),
    "PP-unstable": "the checks hold but a non-finite step appears (the five steps on MPS or any timed step)",
    "PP-mps-fallback": "the checks hold only with a declared fallback; the fine-tune must use it",
    "PP-mps": "every check holds on LOUDAR's own path, and 200 finite steps",
}
ENCODER_MODES = ("mps", "cpu")                      # LOUDAR's own path first, then the declared fallback
CLIP_MODES = ("native", "foreach_false", "cpu")     # clip_grad_norm_ as called; foreach=False; the norm on the CPU
FALLBACK_NAMES = {("encoder", "cpu"): "the encoder on the CPU", ("clip", "foreach_false"): "clip_grad_norm_ with "
                  "foreach=False", ("clip", "cpu"): "the clip norm computed on the CPU"}
WEIGHT_SUFFIXES = (".pt", ".pth", ".ckpt", ".safetensors", ".bin", ".pkl", ".pickle", ".npz")
DATA_SUFFIXES = (".wav", ".flac", ".mp3", ".m4a", ".aif", ".aiff", ".ogg", ".npy", ".npz", ".zip", ".tar", ".gz")
RENDER_PATTERNS = ("au_render_server",)
TORCH_PATTERNS = (r"tools/[^ ]*venv[^ /]*/bin/python", r"-m learn\.[a-z_0-9]+ (fit|train|curve)")

# LOUDAR's files at loudar_run.LOUDAR_COMMIT (each equal to tools/loudar-code-fetch.json's record)
LOUDAR_FILES = {
    "training/trainer.py": "ebe72ed12ace515571aa5924094f0215b7fa02a42b6cfdfa0e26a988d142897f",
    "diff_params/diffusion_latent.py": "551c874467a499c7b3634b59da6629851cf0f135071172a75dc36b2135d45ac8",
    "networks/dit.py": "fe7529323b52eecf45db4113daf41a9493b0c2f4285298dfdd2061cd40ca3088",
    "networks/transformer.py": "116b1da3bd61c1a721b444377f2ae278b410922ee2401569caae7befb5287c6d",
    "utils/normalization.py": "00940169377080a6baf42f0c6a9b781332fe185ab95f6725b477b690574b882d",
    "datasets/GuitarFx.py": "bb47ef30833969081572aaa90f2b7c4dd455618b4b8bd7db2b7870334c096eef",
    "conf/config_train_GuitarFx.yaml": "45b819d7c7cacf9a3c90746d3d55dfd00544816c6e0b70804d8026d47087f52d",
    "conf/exp/GuitarFx.yaml": "556d70ae3063d352af94586395bb753e4533725def8cbeb7fe795421d4c136d4",
    "conf/diff_params/FM_m2l.yaml": "55b0eb677b6d06792a0d2dcf3b5676fc0014ddd69c0437f2d721ae782da6f966",
    "conf/network/dit_M2L.yaml": "fe332e6766b76f7fff0bc20607314933b681f35e64e2961a8d580a0432258cbb",
    "conf/dset/GuitarFx.yaml": "b49183f39d0358c3b79c87deb21bba6c66e68945c14e8ebded15919cd8cd45f7",
    "conf/logging/base_logging.yaml": "938ffb4778059b461954a2e75cdbc2002c8690e055c5c413207ba71b308fe2e0",
}
# The functions that run, by the sha256 of their source text (`function_source`: the def's lines as in the file)
LOUDAR_FUNCS = {
    ("training/trainer.py", "Trainer.train_step"): "f9d23befdbed4cb72cd4e06863379a513c84390f4f1f31033abb512883d69c87",
    ("training/trainer.py", "Trainer.update_ema"): "ceaea5c1a0b3f65020a0271ec7b374e3ed9097112a229db169bf801311e8dcf4",
    ("training/trainer.py", "Trainer.get_batch"): "297e4ff4740ac9765690486d2bf4df45d78eee2a748b592f7d81a25f48ae83ba",
    ("diff_params/diffusion_latent.py", "FM.loss_fn"): "5561b34833dceb1136a1ecef187cd0f4246ac168d8baa5ec7ee1eb8b19323f5f",
    ("diff_params/diffusion_latent.py", "FM.prepare_train_preconditioning"):
        "e2e6c5d73c38a70e600af2597cd0117819f12e33cd2db7a70e5199c04f3f98ae",
    ("diff_params/diffusion_latent.py", "FM.sample_time_training"):
        "e8af60906bf19fc6ad84d283dc079240c0625579dafd2b2cfefd3a796d9b4b2b",
    ("diff_params/diffusion_latent.py", "FM.sample_prior"): "6547918742d8010ea916b359ceac09fc0002b970cb20dfd5b95a276e3272770c",
    ("diff_params/diffusion_latent.py", "FM.transform_fwd"): "a241b38778f28561ca1f89424d75ab8a86b719741dde0cdece87f8ad84492ad2",
    ("diff_params/diffusion_latent.py", "Diffusion.transform_fwd"):
        "2a7ba778839533c91aebad939ec4a3df61b8a20653295882e0519dc3f0c3e5e1",
    ("utils/normalization.py", "apply_RMS_normalization"): "c9fd7b3741909a0fcda5bec6cdd9fe943c02f3a2196ea669bb8d619ac679a685",
    ("utils/normalization.py", "compute_log_rms_gated_max"):
        "2144b7ef3ce75a583654000dcc6debd1c41ee83dee02f236311fa041947dee5f",
}
PLACEHOLDER_MODULES = ("utils.log", "utils.training_utils")   # imported by trainer.py, never used by these methods
DEFAULTS_EXPECT = {"dset": "GuitarFx", "network": "dit_M2L", "diff_params": "FM_m2l",
                   "tester": "only_unconditional_lincae_FM", "exp": "GuitarFx", "logging": "base_logging"}
CONFIG_EXPECT = {      # the composed config's values the probe relies on (config_refusal)
    "exp.batch_size": 2, "exp.audio_len": SEG, "exp.sample_rate": SR, "exp.optimizer._target_": "torch.optim.AdamW",
    "exp.optimizer.lr": 1e-4, "exp.optimizer.weight_decay": 0.01, "exp.optimizer.betas": [0.9, 0.999],
    "exp.optimizer.eps": 1e-8, "exp.use_grad_clip": True, "exp.max_grad_norm": MAX_NORM, "exp.ema_rate": 0.9999,
    "exp.ema_rampup": 10000, "exp.randomize_segment_length": False,
    "diff_params._target_": "diff_params.diffusion_latent.FM", "diff_params.autoencoder_id": "m2l",
    "diff_params.sigma_data": 1, "diff_params.t_min": 1e-5, "diff_params.t_max": 1,
    "network._target_": "networks.dit.DiffusionTransformer", "network.io_channels": 64, "network.embed_dim": 512,
    "network.depth": 16, "network.num_heads": 16,
    "dset.train._target_": "datasets.GuitarFx.GuitarFxIterable", "dset.train.seg_len": SEG,
    "dset.train.rms_normalize": RMS_DB, "logging.log": False, "logging.log_spectrograms": False,
}

# The terms (amendment 5): research use only; nothing ships
TERMS = {
    "loudar_code": "MIT (michalsvento/loudar at loudar_run.LOUDAR_COMMIT)",
    "loudar_checkpoint": ("GuitarFx-175000.pt: tagged MIT on Hugging Face (msvento/loudar at loudar_run.LOUDAR_REVISION), "
                          "trained on GOAT (CC BY-NC, granted on request)"),
    "m2l_autoencoder": ("linear-cae 0.1.4's m2l (BernardoTorres/linear_consistency_autoencoders), Apache-2.0 as the "
                        "codec manifest and the ledger's phase_scratch_codec record it (a retrained Music2Latent; not "
                        "Music2Latent's CC BY-NC weights)"),
    "goat": "CC BY-NC, granted on request; the prior's own training data",
    "use": "research use only; no model is kept and nothing ships",
}

# --- hours (amendment 4) ------------------------------------------------------------------------------------------------
GOAT_RULED_OUT = ("item_5",)           # note_transcribe.RULED_OUT: the user's "Bad DI, don't use it" (2026-11-23)
LEFT_OUT_BANDS = ("Silent Waves", "Drowning")   # untrusted (the trusted-data rule; scratch_search.PANEL_LEFT_OUT)
LIBRARY_ORDER = ("untrusted", "left-out band", "held band", "held out", "reserve DI", "user DI mark", "hum superset",
                 "draw section")       # a section is counted under the first reason that holds
GOAT_ORDER = ("ruled out", "draw item", "5C: no screened window", "5C: DI near full scale")
NOT_COUNTED = {
    "MedleyDB": "the panel's source: test bands, and multitrack stems with no stored DI screen",
    "sets 4 to 6 (incl. BKS)": "held out (clean_di.refuse_held_out; BKS and the panel are the deciding test bands)",
    "intakes outside the clean-DI library manifest (cambridge-new, telefunken-new)": "no stored section screen",
    "Guitar-TECHS P3": "never used (clean_di.refuse_held_out)",
}


# --- the pure rules -----------------------------------------------------------------------------------------------------

def tag(s):
    """(Pure.) A name's public 12-hex tag (git gets no item ids, part keys or paths)."""
    return hashlib.sha256(str(s).encode()).hexdigest()[:12]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def file_sha(path):
    return LR.file_sha(path)


def function_source(text, qualname):
    """(Pure.) A function's source as it stands in a file: its lines from the first decorator (or the def) to its last,
    joined with newlines, and the first line's number. qualname "Class.method" or "function". -> (source, lineno)."""
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)        # LOUDAR's trainer.py has a "\d" in a plain string
        tree = ast.parse(text)
    parts = qualname.split(".")
    body = tree.body
    node = None
    for i, name in enumerate(parts):
        want = ast.ClassDef if i < len(parts) - 1 else (ast.FunctionDef, ast.AsyncFunctionDef)
        node = next((n for n in body if isinstance(n, want) and n.name == name), None)
        if node is None:
            raise KeyError(f"{qualname}: no {name}")
        body = node.body
    first = min([node.lineno] + [d.lineno for d in node.decorator_list])
    lines = text.splitlines()
    return "\n".join(lines[first - 1:node.end_lineno]), first


def source_sha(text, qualname):
    """(Pure.) sha256 of `function_source`'s text."""
    return sha256_bytes(function_source(text, qualname)[0].encode())


def pin_refusals(file_shas, func_shas, files=None, funcs=None):
    """(Pure.) The pins that fail: file_shas {rel path: sha256 or None}, func_shas {(rel path, qualname): sha256 or
    None}. -> sorted list of what differs (empty when every pin holds)."""
    files = LOUDAR_FILES if files is None else files
    funcs = LOUDAR_FUNCS if funcs is None else funcs
    bad = [f"{f}: sha256 not the pin" for f, s in files.items() if file_shas.get(f) != s]
    bad += [f"{f} {q}: source sha256 not the pin" for (f, q), s in funcs.items() if func_shas.get((f, q)) != s]
    return sorted(bad)


def flat(d, prefix=""):
    """(Pure.) A nested dict flattened to dotted keys (lists kept as values)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def _same(a, b):
    if isinstance(b, bool) or isinstance(a, bool):
        return a is b
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=0.0)
        except (TypeError, ValueError):
            return False
    if isinstance(b, (list, tuple)):
        return isinstance(a, (list, tuple)) and len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def defaults_refusal(defaults):
    """(Pure.) config_train_GuitarFx.yaml's defaults list must name the expected group configs. defaults: the list as
    loaded (strings and one-key dicts). -> why, or None."""
    got = {}
    for d in defaults or []:
        if isinstance(d, dict):
            for k, v in d.items():
                if not str(k).startswith("override "):
                    got[str(k)] = v
    bad = {k: got.get(k) for k, v in DEFAULTS_EXPECT.items() if got.get(k) != v}
    return f"config_train_GuitarFx.yaml's defaults differ: {bad}" if bad else None


def config_refusal(cfg):
    """(Pure.) The composed config (a plain dict: exp, diff_params, network, dset, logging) against CONFIG_EXPECT.
    -> why, or None."""
    f = flat(cfg)
    bad = {k: f.get(k, "<missing>") for k, v in CONFIG_EXPECT.items() if not _same(f.get(k, "<missing>"), v)}
    return f"the composed training config differs from the declared: {bad}" if bad else None


def rel(diff, ref):
    """(Pure.) diff / |ref|, or diff itself when ref is 0 (an absolute error then)."""
    return diff / abs(ref) if ref else diff


def scalar_check(dev, cpu, tol, f64=None, mult=CALIB_MULT, ref_ok=True, cap=CALIB_CAP):
    """(Pure.) One figure on MPS against the CPU's: relative error at most `tol`, or calibrated: its error against the
    float64 reference within `mult` times the CPU's own. Calibration is allowed only when the reference holds (`ref_ok`,
    and the CPU's own error against float64 within `tol` and under `cap`); otherwise only the direct check applies and
    the record says so. -> {"err", "pass", "how", "calibration", ...}."""
    vals = (dev, cpu) + ((f64,) if f64 is not None else ())
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals):
        return {"dev": dev, "cpu": cpu, "f64": f64, "err": None, "pass": False, "how": "non-finite",
                "calibration": "not reached"}
    err = rel(abs(dev - cpu), cpu)
    out = {"dev": dev, "cpu": cpu, "f64": f64, "err": err, "tol": tol}
    if f64 is None:
        cal = "no float64 reference"
    else:
        e_dev, e_cpu = rel(abs(dev - f64), f64), rel(abs(cpu - f64), f64)
        out.update(err_dev_f64=e_dev, err_cpu_f64=e_cpu)
        cal = ("refused: the reference does not hold" if not ref_ok else
               "refused: the CPU's own error against float64 is above the tolerance" if e_cpu > tol else
               "refused: the CPU's own error against float64 is above the cap" if e_cpu > cap else "allowed")
    out["calibration"] = cal
    if err <= tol:
        return dict(out, **{"pass": True, "how": "direct"})
    if cal != "allowed":
        return dict(out, **{"pass": False, "how": f"missed; direct only ({cal})"})
    ok = out["err_dev_f64"] <= mult * out["err_cpu_f64"]
    return dict(out, **{"pass": ok, "how": "calibrated" if ok else "missed; calibration failed"})


def reference_holds(cpu_loss, f64_loss, rows, same_draws, tol_loss=None, tol_grad=None):
    """(Pure.) Whether the float64 reference may calibrate a run (the review of #666, fix 2): CPU float32 against
    float64 within the direct tolerances on the loss (1e-4) and on the global gradient (1e-3), and t and the noise the
    same on both devices. rows: `tensor_check`'s rows for the gradients before the clip. -> {"holds", "why", ...}."""
    tol_loss = TOL["loss"] if tol_loss is None else tol_loss
    tol_grad = TOL["grad"] if tol_grad is None else tol_grad
    why = []
    if not same_draws:
        why.append("t or the noise differ between the devices")
    le = None
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (cpu_loss, f64_loss)):
        why.append("no finite float64 loss")
    else:
        le = rel(abs(cpu_loss - f64_loss), f64_loss)
        if le > tol_loss:
            why.append(f"the CPU's loss is {le:.2e} off float64 (tolerance {tol_loss})")
    vals = [r for r in rows.values() if not r.get("none")]
    ge = None
    if not vals or not all("ref64" in r and "cpu64" in r for r in vals):
        why.append("no float64 gradients")
    else:
        ge = rel(math.sqrt(sum(r["cpu64"] ** 2 for r in vals)), math.sqrt(sum(r["ref64"] ** 2 for r in vals)))
        if not math.isfinite(ge) or ge > tol_grad:
            why.append(f"the CPU's global gradient is {ge:.2e} off float64 (tolerance {tol_grad})")
    return {"holds": not why, "why": why, "loss_err_cpu_f64": le, "grad_err_cpu_f64": ge}


def tensor_check(rows, tol, mult=CALIB_MULT, floor_frac=PER_TENSOR_FLOOR, ref_ok=True, cap=CALIB_CAP):
    """(Pure.) Every tensor on MPS against the CPU's, per tensor and globally (amendment 2).

    rows {name: {"ref": |cpu|, "diff": |dev - cpu|, and when the float64 reference exists "ref64": |f64|, "dev64":
    |dev - f64|, "cpu64": |cpu - f64|}} (L2 norms), or {"none": "both"} for a tensor with no value on either device,
    {"none": "dev"} / {"none": "cpu"} when only one lacks it (a failure). A tensor's error is diff / max(ref, floor)
    with floor = floor_frac x the RMS of the refs (and likewise against float64). A tensor or the global figure that
    misses `tol` passes only if its error against float64 is within `mult` x the CPU's own, and only when the reference
    holds: `ref_ok`, and the CPU's own global error against float64 within `tol`; a tensor whose own CPU error against
    float64 is above `cap` (0.1) is never calibrated. Otherwise only direct checks apply, and the row says so.
    -> the table row."""
    both_none = sorted(k for k, r in rows.items() if r.get("none") == "both")
    one_none = sorted(k for k, r in rows.items() if r.get("none") in ("dev", "cpu"))
    vals = {k: r for k, r in rows.items() if not r.get("none")}
    if not vals:
        return {"pass": False, "why": "no tensors", "none_both": both_none, "none_one": one_none}
    nums = [x for r in vals.values() for x in (r["ref"], r["diff"], r.get("ref64", 0.0), r.get("dev64", 0.0),
                                               r.get("cpu64", 0.0))]
    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in nums):
        bad = sorted(k for k, r in vals.items() if not all(math.isfinite(r.get(f, 0.0)) for f in
                                                           ("ref", "diff", "ref64", "dev64", "cpu64")))
        return {"pass": False, "why": "non-finite", "nonfinite_tensors": bad, "none_both": both_none,
                "none_one": one_none}
    has64 = all("ref64" in r and "dev64" in r and "cpu64" in r for r in vals.values())
    k = len(vals)
    rms = math.sqrt(sum(r["ref"] ** 2 for r in vals.values()) / k)
    floor = floor_frac * rms
    out = {"tol": tol, "tensors": k, "floor": floor}
    floor64 = None
    if has64:
        rms64 = math.sqrt(sum(r["ref64"] ** 2 for r in vals.values()) / k)
        floor64 = floor_frac * rms64
        gref64 = math.sqrt(sum(r["ref64"] ** 2 for r in vals.values()))
        gd = rel(math.sqrt(sum(r["dev64"] ** 2 for r in vals.values())), gref64)
        gc = rel(math.sqrt(sum(r["cpu64"] ** 2 for r in vals.values())), gref64)
        out.update(global_err_dev_f64=gd, global_err_cpu_f64=gc)
        cal = ("refused: the reference does not hold" if not ref_ok else
               "refused: the CPU's own global error against float64 is above the tolerance" if gc > tol else
               "allowed")
    else:
        cal = "no float64 reference"
    out["calibration"] = cal
    per, failing, calibrated, capped = {}, [], [], []
    for name, r in sorted(vals.items()):
        den = max(r["ref"], floor)
        e = r["diff"] / den if den else r["diff"]
        ok = e <= tol
        if not ok and cal == "allowed":
            d64 = max(r["ref64"], floor64)
            ed, ec = (r["dev64"] / d64, r["cpu64"] / d64) if d64 else (r["dev64"], r["cpu64"])
            if ec > cap:
                capped.append(name)
            else:
                ok = ed <= mult * ec
                if ok:
                    calibrated.append(name)
        per[name] = e
        if not ok:
            failing.append(name)
    gref = math.sqrt(sum(r["ref"] ** 2 for r in vals.values()))
    gdiff = math.sqrt(sum(r["diff"] ** 2 for r in vals.values()))
    g = rel(gdiff, gref)
    g_ok, g_how = g <= tol, "direct"
    if not g_ok and cal == "allowed":
        g_ok, g_how = out["global_err_dev_f64"] <= mult * out["global_err_cpu_f64"], "calibrated"
    worst = max(per, key=lambda n: per[n])
    out.update({"global_err": g, "global_pass": g_ok, "global_how": g_how, "worst_tensor": worst,
                "worst_err": per[worst], "failing": failing, "calibrated": calibrated, "capped": capped,
                "float64": has64, "none_both": both_none, "none_one": one_none,
                "pass": bool(g_ok and not failing and not one_none)})
    return out


def encoder_verdict(err, f64, tol=None, mult=CALIB_MULT, cap=CALIB_CAP):
    """(Pure.) The encoder's own latent check, which alone judges the encoder (the review of #666, fix 1): MPS
    latents against the CPU's at most 1e-3 relative L2, or calibrated against a float64 encoder only when that
    reference holds (the CPU's own error against it within 1e-3 and under the cap). f64: {"dev", "cpu"} relative
    errors against float64, or None. -> the row."""
    tol = TOL["encoder"] if tol is None else tol
    out = {"err": err, "tol": tol, "f64": f64}
    if f64 is None:
        cal = "no float64 reference"
    elif not (math.isfinite(f64["cpu"]) and f64["cpu"] <= tol and f64["cpu"] <= cap):
        cal = "refused: the CPU's own error against float64 is above the tolerance"
    else:
        cal = "allowed"
    out["calibration"] = cal
    if isinstance(err, (int, float)) and math.isfinite(err) and err <= tol:
        return dict(out, **{"pass": True, "how": "direct"})
    if cal != "allowed":
        return dict(out, **{"pass": False, "how": f"missed; direct only ({cal})"})
    ok = math.isfinite(f64["dev"]) and f64["dev"] <= mult * f64["cpu"]
    return dict(out, **{"pass": bool(ok), "how": "calibrated" if ok else "missed; calibration failed"})


def clip_check(norm, cpu_norm, nonfinite, after, f64_norm=None, tol=TOL["clip_norm"], ref_ok=True):
    """(Pure.) The clip on MPS: its returned norm against the CPU's (`scalar_check`), no non-finite value in the norm
    or the gradients after it, and the gradients after it (`tensor_check`'s row `after`). Records whether it scaled
    (the CPU's norm above MAX_NORM). -> the row."""
    n = scalar_check(norm, cpu_norm, tol, f64=f64_norm, ref_ok=ref_ok)
    ok = bool(n["pass"] and nonfinite == 0 and after.get("pass"))
    scaled = (cpu_norm > MAX_NORM) if isinstance(cpu_norm, (int, float)) and math.isfinite(cpu_norm) else None
    return {"norm": n, "nonfinite": nonfinite, "after": after, "scaled": scaled, "pass": ok}


def nonfinite_step(loss, norm, params_finite):
    """(Pure.) The probe's non-finite step: its loss, the clip's returned norm, or any parameter at its end is not
    finite."""
    def bad(v):
        return v is None or not isinstance(v, (int, float)) or not math.isfinite(v)
    return bool(bad(loss) or bad(norm) or not params_finite)


def error_kind(type_name, message):
    """(Pure.) An MPS failure's kind: "oom" (MPS out of memory), "unsupported" (an op MPS does not implement), or
    "other" (stops the probe, to the orchestrator)."""
    m = (message or "").lower()
    if "out of memory" in m:
        return "oom"
    if type_name == "NotImplementedError" or "not currently implemented for the mps device" in m or \
            "not supported on mps" in m or "unsupported" in m and "mps" in m:
        return "unsupported"
    return "other"


def op_named(message):
    """(Pure.) The op an MPS "not implemented" message names ("aten::name"), else None."""
    m = re.search(r"aten::[A-Za-z0-9_.]+", message or "")
    return m.group(0) if m else None


def pp_code(anomaly, cpu_only, nonfinite, fallbacks):
    """(Pure.) The probe's code, the first that holds in CODES' order. anomaly, cpu_only, fallbacks: lists of reasons;
    nonfinite: the non-finite MPS steps. -> (code, why)."""
    if anomaly:
        return "PP-anomaly", list(anomaly)
    if cpu_only:
        return "PP-cpu-only", list(cpu_only)
    if nonfinite:
        return "PP-unstable", [f"{nonfinite} non-finite MPS steps"]
    if fallbacks:
        return "PP-mps-fallback", list(fallbacks)
    return "PP-mps", []


def table_guard():
    """(Pure.) CODES, PP_TABLE and pp_code agree: every code reachable, in the declared order."""
    if set(CODES) != set(PP_TABLE) or len(CODES) != len(PP_TABLE):
        raise SystemExit("CODES and PP_TABLE differ")
    hits = [pp_code(["a"], [], 0, [])[0], pp_code([], ["c"], 0, [])[0], pp_code([], [], 1, [])[0],
            pp_code([], [], 0, ["f"])[0], pp_code([], [], 0, [])[0]]
    if tuple(hits) != CODES:
        raise SystemExit(f"pp_code's order {hits} is not CODES")


def block_rate(seconds, warmup):
    """(Pure.) A timed block's rate from its per-step seconds: the steps after `warmup` (21-200 of 200). -> {steps,
    rate (steps/s), mean_s, median_s, warmup_mean_s}."""
    rest = list(seconds[warmup:])
    if not rest or any(not (isinstance(s, (int, float)) and math.isfinite(s) and s > 0) for s in rest):
        return {"steps": len(rest), "rate": None, "mean_s": None, "median_s": None, "warmup_mean_s": None}
    srt = sorted(rest)
    n = len(srt)
    med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
    warm = list(seconds[:warmup])
    return {"steps": n, "rate": n / sum(rest), "mean_s": sum(rest) / n, "median_s": med,
            "warmup_mean_s": sum(warm) / len(warm) if warm else None}


def projections(rate, batch=BATCH, seg=SEG, sr=SR):
    """(Pure.) From steps per second: seconds and hours per 1,000 steps, hours for the released checkpoint's 175,000
    steps, and the audio a 1,000 steps see (6.09 h at batch 2 and 526,080 samples). No target count is chosen."""
    audio_h = 1000 * batch * seg / sr / 3600
    if not rate or not math.isfinite(rate) or rate <= 0:
        return {"s_per_1000": None, "h_per_1000": None, "h_175000": None, "audio_h_per_1000": audio_h}
    return {"s_per_1000": 1000 / rate, "h_per_1000": 1000 / rate / 3600, "h_175000": RELEASED_STEPS / rate / 3600,
            "audio_h_per_1000": audio_h}


def split_rate(step_s, encode_s):
    """(Pure.) The encode and network shares of a step's mean seconds, the encode share from its own block."""
    if step_s is None or encode_s is None:
        return {"encode_s": encode_s, "network_s": None}
    return {"encode_s": encode_s, "network_s": step_s - encode_s}


def cpu_rate(seconds, span=CPU_RATE_STEPS):
    """(Pure.) The CPU rate from the five steps' seconds, steps 2 to 5 (1-based). -> steps/s or None."""
    s = list(seconds[span[0] - 1:span[1]])
    if len(s) != span[1] - span[0] + 1 or any(not (isinstance(x, (int, float)) and x > 0) for x in s):
        return None
    return len(s) / sum(s)


def batch_indices(step, n=N_SEGMENTS, batch=BATCH):
    """(Pure.) The segments of step `step` (0-based), cycled: (2k, 2k+1) mod 16."""
    return [(batch * step + i) % n for i in range(batch)]


def segment_rule(items, drawn, ruled_out=GOAT_RULED_OUT, n=N_SEGMENTS, seed=SEED, seconds=SEG / SR):
    """(Pure.) The 16 GOAT segments: items outside the fs draw, never item_5, with 5C's screened window (start_s set,
    no 5C `out` but "no clean/crunch render", which is about the renders, not the DI); in a seeded order, the first n
    whose window start plus 10.96 s lies inside the item. Each segment starts at 5C's window. items: {item: {start_s,
    seconds, out?}}. -> [{"item", "start_s"}]."""
    ok = []
    for it in sorted(items):
        r = items[it]
        if it in ruled_out or it in drawn or r.get("start_s") is None:
            continue
        if r.get("out") not in (None, "no clean/crunch render"):
            continue
        ok.append(it)
    random.Random(f"{seed}|segments").shuffle(ok)
    out = [{"item": it, "start_s": float(items[it]["start_s"])} for it in ok
           if float(items[it]["start_s"]) + seconds <= float(items[it]["seconds"])][:n]
    if len(out) < n:
        raise SystemExit(f"only {len(out)} GOAT items meet the segment rule, not {n}")
    return out


def drawn_goat_items(parts):
    """(Pure.) The GOAT items of the fs draw's parts (cluster "goat|<item>")."""
    return sorted({p["cluster"].split("|", 1)[1] for p in parts if p.get("set") == "goat"})


def idle_counts(matches, exclude):
    """(Pure.) The idle rule's counts. matches {"render": {pid: command}, "torch": {pid: command}} (pgrep -fl per
    pattern); exclude: the probe's own pid and its parents. -> {"render": n, "torch": n, "idle": bool, "pids": ...}."""
    out = {}
    for kind in ("render", "torch"):
        out[kind] = sorted(int(p) for p in (matches.get(kind) or {}) if int(p) not in exclude)
    return {"render": len(out["render"]), "torch": len(out["torch"]), "idle": not out["render"] and not out["torch"],
            "pids": out}


def open_event_class(path, mode, flags, home, read_roots, write_root, models, data_root):
    """(Pure.) One `open` audit event's class: None (allowed), "read-outside" (a file outside the listed roots read
    under the data root, or an audio or array file read anywhere under the home directory), "write-outside" (a write
    under the home directory outside the probe's folder; HF lock files under the models folder allowed), or
    "weights-write" (a weights-like file opened for writing anywhere). Library configuration reads elsewhere under the
    home directory are not data and are not counted."""
    if not isinstance(path, str):
        return None
    p = os.path.normpath(path)
    write = False
    if isinstance(mode, str) and any(c in mode for c in "wax+"):
        write = True
    if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC):
        write = True

    def under(root):
        r = os.path.normpath(root)
        return p == r or p.startswith(r.rstrip(os.sep) + os.sep)
    if write and p.lower().endswith(WEIGHT_SUFFIXES):
        return "weights-write"
    if not under(home):
        return None
    if write:
        if under(write_root):
            return None
        if under(models) and p.endswith(".lock"):
            return None
        return "write-outside"
    if any(under(r) for r in read_roots):
        return None
    return "read-outside" if under(data_root) or p.lower().endswith(DATA_SUFFIXES) else None


def probe_files_refusal(files, segment_names):
    """(Pure.) The probe folder's files (relative paths): only .json anywhere, and the segments' .npy files prep
    listed under segments/. -> the offending files (a weights file or anything else written)."""
    allowed = {f"segments/{n}" for n in segment_names}
    return sorted(f for f in files if not (f.endswith(".json") or f in allowed))


def keys_refusal(local, main, prefix=KEY):
    """(Pure.) This checkout's `phase_scratch_prior_probe*` keys must equal main's. -> why, or None."""
    a = {k: v for k, v in (local or {}).items() if k.startswith(prefix)}
    b = {k: v for k, v in (main or {}).items() if k.startswith(prefix)}
    if prefix not in b:
        return f"main's {LEDGER_ID} entry has no {prefix}: merge the declaration before running"
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return f"this checkout's {', '.join(diff)} differ from main's: pull main" if diff else None


def section_reasons(sec, rules):
    """(Pure.) Why a clean-DI library section is not counted, every reason that holds in LIBRARY_ORDER. sec: a
    manifest row (di, band, path, start_s, clean, disjoint, training_ok, split). rules: {"left_out_bands": set,
    "held_bands": {band: [why]}, "held_out": {path: why}, "reserve": set of di, "marked": set of di, "hum": set of di,
    "draw": set of (di, start_s)}. -> [reason]."""
    out = []
    if not (sec.get("training_ok") and sec.get("clean") and sec.get("disjoint") and sec.get("split") == "library"):
        out.append("untrusted")
    if sec.get("band") in rules.get("left_out_bands", ()):
        out.append("left-out band")
    if rules.get("held_bands", {}).get(sec.get("band")):
        out.append("held band")
    if sec.get("path") in rules.get("held_out", {}):
        out.append("held out")
    if sec.get("di") in rules.get("reserve", ()):
        out.append("reserve DI")
    if sec.get("di") in rules.get("marked", ()):
        out.append("user DI mark")
    if sec.get("di") in rules.get("hum", ()):
        out.append("hum superset")
    if (sec.get("di"), float(sec.get("start_s", -1))) in rules.get("draw", ()):
        out.append("draw section")
    return out


def library_tally(sections, rules):
    """(Pure.) The library's trusted hours by source and set, and what each exclusion removed (a section counted under
    its first reason in LIBRARY_ORDER). -> {"hours", "by_source", "excluded": {reason: {"sections", "hours"}},
    "held_band_reasons": {why: hours}}."""
    by, ex, held = {}, {r: {"sections": 0, "hours": 0.0} for r in LIBRARY_ORDER}, {}
    total = 0.0
    for s in sections:
        h = (float(s["end_s"]) - float(s["start_s"])) / 3600
        why = section_reasons(s, rules)
        if why:
            first = min(why, key=LIBRARY_ORDER.index)
            ex[first]["sections"] += 1
            ex[first]["hours"] += h
            if first == "held band":
                for w in rules["held_bands"][s["band"]]:
                    held[w] = held.get(w, 0.0) + h
            continue
        k = f"{s.get('source')} / {s.get('set')}"
        by.setdefault(k, {"sections": 0, "hours": 0.0})
        by[k]["sections"] += 1
        by[k]["hours"] += h
        total += h
    return {"hours": total, "by_source": dict(sorted(by.items())), "excluded": ex, "held_band_reasons": held}


def goat_tally(items, drawn, ruled_out=GOAT_RULED_OUT):
    """(Pure.) GOAT's hours apart: each item's full DI length (5C's measured seconds) less, first that holds, the
    ruled-out item, the drawn items, and 5C's no-screened-window and near-full-scale items. items {item: {seconds,
    out?, tuning?}}. -> {"hours", "items", "excluded": {reason: {"items", "hours"}}, "by_tuning": {tuning: hours}}."""
    ex = {r: {"items": 0, "hours": 0.0} for r in GOAT_ORDER}
    total, n, tun = 0.0, 0, {}
    for it in sorted(items):
        r = items[it]
        h = float(r["seconds"]) / 3600
        why = ("ruled out" if it in ruled_out else "draw item" if it in drawn else
               "5C: no screened window" if r.get("out") == "no window" else
               "5C: DI near full scale" if r.get("out") == "DI near full scale" else None)
        if why:
            ex[why]["items"] += 1
            ex[why]["hours"] += h
            continue
        total += h
        n += 1
        t = str(r.get("tuning"))
        tun[t] = tun.get(t, 0.0) + h
    return {"hours": total, "items": n, "excluded": ex, "by_tuning": dict(sorted(tun.items()))}


# --- paths, the guard, JSON ---------------------------------------------------------------------------------------------

def pf_dir(data_dir=None):
    return pathlib.Path(data_dir or DATA).expanduser() / PF_SUB


def probe_dir(data_dir=None):
    return pf_dir(data_dir) / OUT_SUB


def write_json(path, obj):
    """The probe's only writer in `check`, `time`, `hours` and `read`: a new .json file, never overwritten."""
    p = pathlib.Path(path)
    if p.suffix != ".json":
        raise SystemExit(f"{p.name}: the probe writes only JSON here")
    if p.exists():
        raise SystemExit(f"{p} exists: never overwritten")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".partial.json")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=False, default=str))
    tmp.rename(p)
    return p


def main_entry(text):
    doc = json.loads(text)
    for t in doc["tests"]:
        if t["test_id"] == LEDGER_ID:
            return t
    return None


def local_entry():
    return main_entry(LEDGER.read_text())


def on_main():
    """main's `preset-ladder` entry (origin/main after a fetch), refused unless this checkout's prior_probe.py and
    loudar_run.py are main's and its phase_scratch_prior_probe* keys equal main's. Stdlib only (git)."""
    def git(*a):
        return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)
    git("fetch", "-q", "origin", "main")
    led = git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        raise SystemExit(f"main's ledger is not readable: {led.stderr.strip()}")
    m = main_entry(led.stdout)
    if git("diff", "--quiet", "origin/main", "--", "learn/prior_probe.py", "learn/loudar_run.py").returncode:
        raise SystemExit("this checkout's learn/prior_probe.py or learn/loudar_run.py differs from main's: run merged code")
    why = keys_refusal(local_entry(), m)
    if why:
        raise SystemExit(why)
    return m


def require_on_main():
    table_guard()
    return on_main()


def pgrep(pattern):
    r = subprocess.run(["pgrep", "-fl", pattern], capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        pid, _, cmd = line.strip().partition(" ")
        if pid.isdigit():
            out[int(pid)] = cmd
    return out


def own_lineage():
    """The probe's pid and its parents' (ps), left out of the idle counts."""
    pids, p = {os.getpid()}, os.getppid()
    while p and p not in pids and p > 1:
        pids.add(p)
        r = subprocess.run(["ps", "-o", "ppid=", "-p", str(p)], capture_output=True, text=True)
        p = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    return pids


def machine_state():
    """The idle rule's counts now (amendment 6), with the time."""
    m = {"render": {}, "torch": {}}
    for pat in RENDER_PATTERNS:
        m["render"].update(pgrep(pat))
    for pat in TORCH_PATTERNS:
        m["torch"].update(pgrep(pat))
    out = idle_counts(m, own_lineage())
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return out


def checkpoint_refusal(path):
    """(Stdlib.) The checkpoint's size and sha256 against loudar_run's pins, before torch is imported. -> why, or None."""
    p = pathlib.Path(path)
    if not p.is_file():
        return f"{p}: no checkpoint"
    if p.stat().st_size != LR.CHECKPOINT_SIZE:
        return f"{p.name}: {p.stat().st_size} bytes, not the pinned {LR.CHECKPOINT_SIZE}"
    if file_sha(p) != LR.CHECKPOINT_SHA256:
        return f"{p.name}: sha256 is not the pin"
    return None


def checkpoint_path(models):
    """The checkpoint in the codec models' Hugging Face cache, at the pinned revision (no network)."""
    return (pathlib.Path(models).expanduser() / "hf" / "hub" / "models--msvento--loudar" / "snapshots" /
            LR.LOUDAR_REVISION / LR.CHECKPOINT)


def loudar_shas(src):
    """sha256 of the pinned LOUDAR files and function sources under `src`. -> (file_shas, func_shas)."""
    src = pathlib.Path(src)
    files = {f: (file_sha(src / f) if (src / f).is_file() else None) for f in LOUDAR_FILES}
    funcs = {}
    for f, q in LOUDAR_FUNCS:
        try:
            funcs[(f, q)] = source_sha((src / f).read_text(), q)
        except (OSError, KeyError, SyntaxError):
            funcs[(f, q)] = None
    return files, funcs


# --- hours and prep (main .venv; zero renders) ---------------------------------------------------------------------------

def hours_inputs(data_dir):
    """The stored inventories `hours` reads (zero renders; no audio but EGFxSet's WAV headers)."""
    data = pathlib.Path(data_dir).expanduser()
    pf = pf_dir(data)
    return {"library_manifest": data / "learn/clean-di/manifest.json",
            "library_inventory": data / "learn/clean-di/inventory.json",
            "di_scope_verdicts": pf / "di-scope/verdicts.json", "batch3_marks": pf / "captures3/di-marks.json",
            "draw": pf / "fs/draw.json", "goat_units": pf / "goat/units.json",
            "egdb_manifest": data / "references/datasets-egdb/manifest.json",
            "egfxset_clean": data / "references/datasets/egfxset/Clean"}


def cmd_hours(a):
    """Trusted DI hours per source (amendment 4) -> PF/fs/prior-probe/hours.json (or printed, --dry)."""
    require_on_main() if not a.dry else table_guard()      # --dry writes nothing, so it runs before the merge too
    from learn import capture_labels as CL
    from learn import clean_di as CD
    from learn import pretrain_set as PS
    from learn import window_count as WC

    ins = hours_inputs(a.data_dir)
    man = json.loads(ins["library_manifest"].read_text())
    inv = json.loads(ins["library_inventory"].read_text())
    secs = man["sections"]
    draw = json.loads(ins["draw"].read_text())["parts"]
    marked = set(json.loads(ins["di_scope_verdicts"].read_text())["dropped"])
    marked |= set(json.loads(ins["batch3_marks"].read_text())["di_files"])
    held_out = {}
    for s in secs:
        if s["path"] in held_out:
            continue
        try:
            CD.refuse_held_out(s)
        except ValueError as e:
            held_out[s["path"]] = str(e)
    bands = sorted({s["band"] for s in secs})
    rules = {"left_out_bands": set(LEFT_OUT_BANDS),
             "held_bands": {b: WC.held_reasons(b) for b in bands if b in CL.HELD_BANDS},
             "held_out": held_out, "reserve": set(PS.stage_f_dis(inv)), "marked": marked,
             "hum": set(PS.HUM_SUSPECT),
             "draw": {(p["section"].rsplit("@", 1)[0], float(p["section"].rsplit("@", 1)[1])) for p in draw}}
    lib = library_tally(secs, rules)
    lib["marked_matched"] = len(marked & {s["di"] for s in secs})
    lib["marked_files"] = len(marked)
    goat_items = json.loads(ins["goat_units"].read_text())["items"]
    goat = goat_tally({k: dict(v, tuning=v.get("tuning")) for k, v in goat_items.items()}, set(drawn_goat_items(draw)))
    egdb = json.loads(ins["egdb_manifest"].read_text())["files"]
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {KEY}", "kind": "a count only; the fine-tune declares its own set",
           "inputs": {k: str(v) for k, v in ins.items()},
           "inputs_sha256": {k: file_sha(v) for k, v in ins.items() if v.is_file()},
           "library": dict(lib, rule="training_ok, clean, disjoint, split library (the clean-DI library's screens: "
                           "hum, hiss, bleed, drop-outs, clipping), 10-s sections", order=list(LIBRARY_ORDER)),
           "egdb": {"hours": sum(float(v["seconds"]) for v in egdb.values()) / 3600, "files": len(egdb),
                    "status": "unscreened here: the DIs as stored; LOUDAR's test set, so a fresh source for it"},
           "egfxset": egfxset_hours(ins["egfxset_clean"]),
           "goat": dict(goat, status="the prior's own training data; scope never checked; listed apart",
                        order=list(GOAT_ORDER)),
           "not_counted": NOT_COUNTED, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    out["counted_hours_excluding_goat"] = lib["hours"]
    print(json.dumps({"library_hours": lib["hours"], "by_source": lib["by_source"],
                      "excluded": {k: round(v["hours"], 3) for k, v in lib["excluded"].items()},
                      "egdb_hours": out["egdb"]["hours"], "egfxset_hours": out["egfxset"].get("hours"),
                      "goat_hours": goat["hours"], "goat_items": goat["items"],
                      "goat_excluded": {k: v["items"] for k, v in goat["excluded"].items()}}, indent=1))
    if a.dry:
        print("HOURS DRY: nothing written")
        return
    write_json(probe_dir(a.data_dir) / "hours.json", out)
    print(f"HOURS DONE: {probe_dir(a.data_dir) / 'hours.json'}")


def egfxset_hours(clean):
    """EGFxSet's clean single notes, by WAV header (soundfile.info; no samples read), unscreened."""
    import soundfile as sf

    files = sorted(pathlib.Path(clean).glob("*/*.wav"))
    secs = sum(sf.info(str(f)).duration for f in files)
    return {"hours": secs / 3600, "files": len(files),
            "status": "unscreened here: clean single notes on 5 pickups, the files as stored"}


def cmd_prep(a):
    """The 16 GOAT DI segments (`segment_rule`): mono, 48 kHz (`clean_di.resample`), 526,080 samples from 5C's window,
    float32, not normalised (check and time normalise them with LOUDAR's own rule) -> PF/fs/prior-probe/segments/
    and prep.json (or printed, --dry)."""
    require_on_main() if not a.dry else table_guard()      # --dry writes nothing, so it runs before the merge too
    import io
    import zipfile

    import numpy as np
    import soundfile as sf

    from learn import clean_di as CD
    from learn import pipeline_fix as P

    d = probe_dir(a.data_dir)
    sd = d / "segments"
    if not a.dry and (sd.exists() or (d / "prep.json").exists()):
        raise SystemExit(f"{sd} or prep.json exists: never overwritten")
    pf = pf_dir(a.data_dir)
    units = json.loads((pf / "goat/units.json").read_text())
    drawn = set(drawn_goat_items(json.loads((pf / "fs/draw.json").read_text())["parts"]))
    picks = segment_rule(units["items"], drawn)
    zp = pathlib.Path(a.data_dir).expanduser() / "references/datasets-goat/_zips/GOAT.zip"
    segs = []
    with zipfile.ZipFile(zp) as z:
        meta = {m["item"]: m for m in P.goat_items_from(z)}
        for i, pk in enumerate(picks):
            member = P.goat_member(pk["item"], meta[pk["item"]]["di_audio_path"])
            raw = z.read(member)
            x, sr = sf.read(io.BytesIO(raw), dtype="float64", always_2d=True)
            y = CD.resample(x.mean(1), sr, SR)
            lo = int(round(pk["start_s"] * SR))
            seg = np.asarray(y[lo:lo + SEG], np.float32)
            if len(seg) != SEG or not np.isfinite(seg).all():
                raise SystemExit(f"segment {i}: {len(seg)} samples or non-finite")
            name = f"seg-{i:02d}.npy"
            rms = float(np.sqrt(np.mean(seg.astype(np.float64) ** 2)))
            segs.append({"name": name, "item": pk["item"], "tag": tag(pk["item"]), "start_s": pk["start_s"],
                         "source_sr": sr, "member_sha256": sha256_bytes(raw),
                         "audio_sha256": sha256_bytes(seg.tobytes()), "rms_dbfs": 20 * math.log10(max(rms, 1e-12)),
                         "_seg": seg})
    rec = {"plan": PLAN, "ledger": f"{LEDGER_ID} {KEY}", "seed": SEED, "rule": segment_rule.__doc__.split(".")[0],
           "n": N_SEGMENTS, "samples": SEG, "sr": SR, "normalised": False,
           "normalisation": f"check/time: LOUDAR's apply_RMS_normalization(RMS_norm={RMS_DB}, use_gate=True) per "
                            "segment, as GuitarFxIterable does",
           "resample": "clean_di.resample (scipy resample_poly) from the item's rate to 48 kHz, then 5C's window",
           "zip": str(zp), "drawn_items_excluded": len(drawn), "ruled_out": list(GOAT_RULED_OUT),
           "segments": [{k: v for k, v in s.items() if k != "_seg"} for s in segs],
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    print(json.dumps({"segments": [(s["tag"], s["start_s"], round(s["rms_dbfs"], 1)) for s in segs],
                      "megabytes": N_SEGMENTS * SEG * 4 / 1e6}, indent=1))
    if a.dry:
        print("PREP DRY: nothing written")
        return
    sd.mkdir(parents=True, exist_ok=False)
    for s in segs:
        np.save(sd / s["name"], s["_seg"])
        s_rec = next(r for r in rec["segments"] if r["name"] == s["name"])
        s_rec["file_sha256"] = file_sha(sd / s["name"])
    write_json(d / "prep.json", rec)
    print(f"PREP DONE: {N_SEGMENTS} segments, {d / 'prep.json'}")


# --- LOUDAR (torch inside; $LV) -----------------------------------------------------------------------------------------

class _Placeholder(type(sys)):
    """One of LOUDAR's modules trainer.py imports but train_step/update_ema/get_batch never use: any attribute raises."""

    def __getattr__(self, name):
        raise AttributeError(f"{self.__name__} is a placeholder in the prior probe (never used by the steps): {name}")


class Recorder:
    """The observers: the FM instance's loss_fn, sample_time_training and sample_prior wrapped on the instance (each
    calls the class's own method and keeps a copy of its result), and clip_grad_norm_ wrapped for the run (it keeps
    the gradients before and after and the returned norm, and applies the clip mode in use)."""

    def __init__(self, torch, dp, fm_cls):
        self.torch, self.dp, self.fm = torch, dp, fm_cls
        self.orig_clip = torch.nn.utils.clip_grad_norm_
        self.capture, self.clip_mode, self.names = False, "native", {}
        self.reset()

    def reset(self):
        self.error = self.t = self.z = self.norm = self.pre = self.post = self.clip_error = None

    def install(self):
        dp, fm = self.dp, self.fm

        def loss_fn(net, x, *args, **kw):
            err, sig = fm.loss_fn(dp, net, x, *args, **kw)
            self.error = err.detach()
            return err, sig

        def sample_time_training(n):
            t = fm.sample_time_training(dp, n)
            self.t = t.detach().clone()
            return t

        def sample_prior(shape=None, t=None):
            z = fm.sample_prior(dp, shape=shape, t=t)
            self.z = z.detach().clone()
            return z
        dp.loss_fn, dp.sample_time_training, dp.sample_prior = loss_fn, sample_time_training, sample_prior
        self.torch.nn.utils.clip_grad_norm_ = self.clip

    def uninstall(self):
        for k in ("loss_fn", "sample_time_training", "sample_prior"):
            self.dp.__dict__.pop(k, None)
        self.torch.nn.utils.clip_grad_norm_ = self.orig_clip

    def snapshot(self, params):
        return {self.names.get(id(p), str(i)): (None if p.grad is None else p.grad.detach().to("cpu").clone())
                for i, p in enumerate(params)}

    def clip(self, parameters, max_norm, *args, **kw):
        torch = self.torch
        params = list(parameters)
        if self.capture:
            self.pre = self.snapshot(params)
        try:
            if self.clip_mode == "native":
                norm = self.orig_clip(params, max_norm, *args, **kw)
            elif self.clip_mode == "foreach_false":
                kw = dict(kw, foreach=False)
                norm = self.orig_clip(params, max_norm, *args, **kw)
            else:                                  # the norm on the CPU, torch's own rule applied to the device grads
                grads = [p.grad for p in params if p.grad is not None]
                norm = torch.linalg.vector_norm(torch.stack([torch.linalg.vector_norm(g.detach().to("cpu"), 2)
                                                             for g in grads]), 2)
                coef = torch.clamp(float(max_norm) / (norm + 1e-6), max=1.0)
                for g in grads:
                    g.mul_(coef.to(g.device, g.dtype))
        except Exception as e:
            self.clip_error = e
            raise
        self.norm = norm
        if self.capture:
            self.post = self.snapshot(params)
        return norm


def compose_args(src):
    """The training config as `config_train_GuitarFx.yaml` composes it (its defaults, the groups over `_self_`), with
    logging.log and log_spectrograms False. -> (OmegaConf args, the defaults list)."""
    from omegaconf import OmegaConf

    conf = pathlib.Path(src) / "conf"
    top = OmegaConf.load(conf / "config_train_GuitarFx.yaml")
    defaults = OmegaConf.to_container(top.defaults)
    why = defaults_refusal(defaults)
    if why:
        raise SystemExit(why)
    exp = OmegaConf.merge(top.get("exp", {}), OmegaConf.load(conf / "exp/GuitarFx.yaml"))
    logging_cfg = OmegaConf.merge(OmegaConf.load(conf / "logging/base_logging.yaml"),
                                  {"log": False, "log_spectrograms": False})
    args = OmegaConf.create({"exp": exp, "network": OmegaConf.load(conf / "network/dit_M2L.yaml"),
                             "diff_params": OmegaConf.load(conf / "diff_params/FM_m2l.yaml"),
                             "dset": OmegaConf.load(conf / "dset/GuitarFx.yaml"), "logging": logging_cfg})
    return args, defaults


def import_trainer():
    """LOUDAR's `training.trainer`, with PLACEHOLDER_MODULES standing in during its import only."""
    put = [n for n in PLACEHOLDER_MODULES if n not in sys.modules]
    for n in put:
        sys.modules[n] = _Placeholder(n)
    try:
        import training.trainer as T
    finally:
        for n in put:
            if isinstance(sys.modules.get(n), _Placeholder):
                del sys.modules[n]
    return T


class Audit:
    """The file rule, for check and time: an `open` audit hook classifies every Python-level open
    (`open_event_class`); torch.save raises while the probe runs."""

    def __init__(self, code, models, out_dir, data_root):
        home = str(pathlib.Path.home())
        roots = {sys.prefix, sys.base_prefix, sys.exec_prefix, str(pathlib.Path(code).expanduser().resolve()),
                 str(pathlib.Path(models).expanduser().resolve()), str(pathlib.Path(out_dir).resolve()), str(REPO)}
        self.args = (home, tuple(sorted(roots)), str(pathlib.Path(out_dir).resolve()),
                     str(pathlib.Path(models).expanduser().resolve()), str(pathlib.Path(data_root).expanduser().resolve()))
        self.events = {"read-outside": [], "write-outside": [], "weights-write": []}
        sys.addaudithook(self.hook)

    def hook(self, event, args):
        if event != "open":
            return
        try:
            path = args[0]
            if isinstance(path, bytes):
                path = path.decode(errors="replace")
            if isinstance(path, str):
                path = os.path.abspath(path)
            k = open_event_class(path, args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else None,
                                 *self.args)
            if k and len(self.events[k]) < 50 and path not in self.events[k]:
                self.events[k].append(path)
        except Exception:
            pass

    def anomalies(self):
        out = []
        if self.events["read-outside"]:
            out.append(f"{len(self.events['read-outside'])} files read outside the list")
        if self.events["write-outside"]:
            out.append(f"{len(self.events['write-outside'])} files written outside the probe's folder")
        if self.events["weights-write"]:
            out.append(f"{len(self.events['weights-write'])} weights files opened for writing")
        return out


class Anomaly(Exception):
    """A pin or hash failed before anything of LOUDAR's ran: the command writes its record with PP-anomaly and stops."""

    def __init__(self, reasons, record):
        super().__init__("; ".join(reasons))
        self.reasons, self.record = list(reasons), dict(record)


def no_save(*_a, **_k):
    raise RuntimeError("the prior probe writes no model (torch.save is disabled)")


def setup(a, need_mps=True):
    """The environment, the pins, LOUDAR's config, the FM instance (m2l on the CPU), the network with the released EMA
    weights (on the CPU, as hydra builds it, in training mode), Trainer, and the segments. -> a dict."""
    sys.dont_write_bytecode = True                 # no .pyc into LOUDAR's tree
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"):
        raise SystemExit("PYTORCH_ENABLE_MPS_FALLBACK is set: unset it (an unsupported op must be reported, not hidden)")
    d = probe_dir(a.data_dir)
    audit = Audit(a.code, a.models, d, a.data_dir)
    ck_path = checkpoint_path(a.models)
    src = pathlib.Path(a.code).expanduser() / "src"
    fshas, qshas = loudar_shas(src)
    prep = json.loads((d / "prep.json").read_text())
    seg_names = [s["name"] for s in prep["segments"]]
    anomaly = [w for w in [checkpoint_refusal(ck_path)] if w] + pin_refusals(fshas, qshas)
    anomaly += [f"segments/{s['name']}: sha256 is not prep.json's" for s in prep["segments"]
                if not (d / "segments" / s["name"]).is_file() or file_sha(d / "segments" / s["name"]) !=
                s.get("file_sha256")]
    if anomaly:                                    # before anything of LOUDAR's is imported or loaded
        raise Anomaly(anomaly, {"file_sha256": fshas, "func_sha256": {f"{f} {q}": s for (f, q), s in qshas.items()},
                                "file_events": audit.events})
    LR.set_env(a.models)
    import torch

    import omegaconf
    why = LR.version_refusal(torch.__version__, omegaconf.__version__)
    if why:
        raise SystemExit(why)
    if need_mps and not torch.backends.mps.is_available():
        raise SystemExit("MPS is not available")
    torch.set_num_threads(THREADS)
    torch.save = no_save
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import hydra
    from omegaconf import OmegaConf

    args, defaults = compose_args(src)
    why = config_refusal(OmegaConf.to_container(args, resolve=True))
    if why:
        raise SystemExit(why)
    T = import_trainer()
    from diff_params.diffusion_latent import FM, Diffusion
    from utils.normalization import apply_RMS_normalization

    live = {("training/trainer.py", "Trainer.train_step"): T.Trainer.train_step,
            ("training/trainer.py", "Trainer.update_ema"): T.Trainer.update_ema,
            ("training/trainer.py", "Trainer.get_batch"): T.Trainer.get_batch,
            ("diff_params/diffusion_latent.py", "FM.loss_fn"): FM.loss_fn,
            ("diff_params/diffusion_latent.py", "FM.prepare_train_preconditioning"): FM.prepare_train_preconditioning,
            ("diff_params/diffusion_latent.py", "FM.sample_time_training"): FM.sample_time_training,
            ("diff_params/diffusion_latent.py", "FM.sample_prior"): FM.sample_prior,
            ("diff_params/diffusion_latent.py", "FM.transform_fwd"): FM.transform_fwd,
            ("diff_params/diffusion_latent.py", "Diffusion.transform_fwd"): Diffusion.transform_fwd,
            ("utils/normalization.py", "apply_RMS_normalization"): apply_RMS_normalization,
            ("utils/normalization.py", "compute_log_rms_gated_max"):
                sys.modules["utils.normalization"].compute_log_rms_gated_max}
    for (f, q), fn in live.items():
        co = fn.__code__
        want = function_source((src / f).read_text(), q)[1]
        if pathlib.Path(co.co_filename).resolve() != (src / f).resolve() or co.co_firstlineno != want:
            anomaly.append(f"{f} {q}: the running function is not the pinned file's")
    dp = hydra.utils.instantiate(args.diff_params)
    if type(dp) is not FM:
        raise SystemExit(f"diff_params is {type(dp).__name__}, not FM")
    net = hydra.utils.instantiate(args.network)
    manifest = json.loads((pathlib.Path(a.models).expanduser() / "manifest.json").read_text())
    ema, ck = LR.load_checkpoint(ck_path, manifest)
    net.load_state_dict(ema)
    del ema
    net = net.to("cpu")
    import numpy as np

    segs = []
    for s in prep["segments"]:
        p = d / "segments" / s["name"]
        x = np.load(p, allow_pickle=False)
        if sha256_bytes(np.ascontiguousarray(x, np.float32).tobytes()) != s["audio_sha256"]:
            anomaly.append(f"segments/{s['name']}: samples are not prep.json's")
        segs.append(torch.from_numpy(np.asarray(x, np.float32)))
    rec = Recorder(torch, dp, FM)
    rec.install()
    return {"torch": torch, "hydra": hydra, "args": args, "defaults": defaults, "T": T, "FM": FM, "dp": dp,
            "base": net, "rms": apply_RMS_normalization, "segs": segs, "rec": rec, "audit": audit,
            "anomaly": anomaly, "checkpoint": ck, "file_sha256": fshas,
            "func_sha256": {f"{f} {q}": s for (f, q), s in qshas.items()}, "prep_sha256": file_sha(d / "prep.json"),
            "seg_names": seg_names, "dir": d}


def normalised(m, length=SEG):
    """The segments cut to `length` and RMS-normalised by LOUDAR's own rule (as GuitarFxIterable)."""
    torch = m["torch"]
    out = []
    for x in m["segs"]:
        y = m["rms"](x[:length].clone().unsqueeze(0).unsqueeze(0), RMS_norm=RMS_DB, use_gate=True).squeeze()
        out.append(y.contiguous())
    return out


def batch_of(m, xs, step, dev):
    torch = m["torch"]
    return torch.stack([xs[i] for i in batch_indices(step)]).to(dev)


def cycled(m, xs, dev):
    """The batches of the 16 segments (8 distinct), built on `dev` before the clock and yielded in step order,
    cycled (`batch_indices`)."""
    import itertools

    return itertools.cycle([batch_of(m, xs, k, dev) for k in range(N_SEGMENTS // BATCH)])


class Encoder:
    """The encoder for a run: LOUDAR's own (`dp.encode`, the m2l autoencoder on `dev`), the CPU fallback (the CPU
    autoencoder, the latents moved to the batch's device), or shared latents (the network-alone run). `last` keeps a
    reference to the latents the last call returned (no copy, no sync), so run 2's CPU reference is fed the MPS run's
    own latents."""

    def __init__(self, m, ae_cpu, ae_mps):
        self.m, self.ae = m, {"cpu": ae_cpu, "mps": ae_mps}
        self.orig = m["dp"].encode                 # LOUDAR's encode_fn (reads dp.autoencoder at each call)
        self.last = None

    def _keep(self, fn):
        def encode(x):
            z = fn(x)
            self.last = z
            return z
        return encode

    def use(self, mode, dev, shared=None):
        dp = self.m["dp"]
        dp.__dict__.pop("encode", None)
        self.last = None
        if shared is not None:
            dp.encode = self._keep(lambda x: shared.to(x.device))
            return
        if mode == "mps" and dev == "mps":
            dp.autoencoder = self.ae["mps"]
            dp.encode = self._keep(self.orig)
        else:                                      # the CPU encoder (on a CPU run, LOUDAR's own path)
            dp.autoencoder = self.ae["cpu"]
            orig = self.orig
            dp.encode = self._keep((lambda x: orig(x.to("cpu")).to(x.device)) if dev != "cpu" else orig)


def stub(m, net, dev, batches, it=0):
    """The object Trainer.train_step and Trainer.update_ema run on: exactly the attributes they read, the optimizer and
    EMA built as Trainer.__init__ builds them, get_batch bound from Trainer.get_batch."""
    import copy
    import types

    s = types.SimpleNamespace()
    s.args, s.network, s.diff_params, s.device, s.it = m["args"], net, m["dp"], m["torch"].device(dev), it
    s.optimizer = m["hydra"].utils.instantiate(m["args"].exp.optimizer, params=net.parameters())
    s.ema = copy.deepcopy(net).eval().requires_grad_(False)
    s.dset = iter(batches)
    s.get_batch = types.MethodType(m["T"].Trainer.get_batch, s)
    m["rec"].names = {id(p): n for n, p in net.named_parameters()}
    return s


def one_step(m, s):
    """One training iteration in training_loop's order: train_step, update_ema, it += 1 (LOUDAR's own methods)."""
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):     # FM.loss_fn prints the latent shape every call
        m["T"].Trainer.train_step(s)
        m["T"].Trainer.update_ema(s)
    s.it += 1


def params_finite(m, net):
    torch = m["torch"]
    return bool(torch.stack([torch.isfinite(p.detach()).all() for p in net.parameters()]).all().item())


def sync(m, dev):
    if dev == "mps":
        m["torch"].mps.synchronize()


def guarded(fn):
    """fn() -> (result, None), or (None, {"kind", "error", "op"}) for an MPS out-of-memory or unsupported op; any other
    error stops the probe."""
    try:
        return fn(), None
    except Exception as e:      # noqa: BLE001 (classified, else re-raised)
        kind = error_kind(type(e).__name__, str(e))
        if kind == "other":
            raise
        return None, {"kind": kind, "error": f"{type(e).__name__}: {str(e)[:400]}", "op": op_named(str(e))}


def norms_rows(m, dev_t, cpu_t, f64_t=None):
    """Per-tensor L2 norms for tensor_check, computed in float64 on the CPU."""
    torch = m["torch"]
    rows = {}
    for k in sorted(set(dev_t) | set(cpu_t)):
        a, b = dev_t.get(k), cpu_t.get(k)
        if a is None or b is None:
            rows[k] = {"none": "both" if a is None and b is None else ("dev" if a is None else "cpu")}
            continue
        a, b = a.double(), b.double()
        r = {"ref": float(torch.linalg.vector_norm(b)), "diff": float(torch.linalg.vector_norm(a - b))}
        c = (f64_t or {}).get(k)
        if c is not None:
            c = c.double()
            r.update(ref64=float(torch.linalg.vector_norm(c)), dev64=float(torch.linalg.vector_norm(a - c)),
                     cpu64=float(torch.linalg.vector_norm(b - c)))
        rows[k] = r
    if f64_t is not None and any("ref64" not in r for r in rows.values() if not r.get("none")):
        for r in rows.values():
            for f in ("ref64", "dev64", "cpu64"):
                r.pop(f, None)
    return rows


def total_norm(m, grads):
    torch = m["torch"]
    g = [v.double() for v in grads.values() if v is not None]
    return float(torch.linalg.vector_norm(torch.stack([torch.linalg.vector_norm(x) for x in g])))


def train_once(m, enc, dev, batch, enc_mode, clip_mode, shared=None, seed=CHECK_SEED):
    """One captured train_step + update_ema from the released weights on `dev`. -> {loss, t, z, norm, pre, post,
    finite, lat} (tensors on the CPU; lat: the latents this run's encoder returned)."""
    import copy

    torch, rec = m["torch"], m["rec"]
    net = copy.deepcopy(m["base"]).to(dev)
    s = stub(m, net, dev, [batch.to(dev)])
    enc.use(enc_mode, dev, shared=shared)
    rec.reset()
    rec.capture, rec.clip_mode = True, clip_mode if dev == "mps" else "native"
    torch.manual_seed(seed)
    try:
        one_step(m, s)
        sync(m, dev)
    finally:
        rec.capture = False
    err = rec.error
    loss = float(err.mean(dim=1).mean())
    out = {"loss": loss, "t": rec.t, "z": rec.z, "norm": float(rec.norm), "pre": rec.pre, "post": rec.post,
           "finite": params_finite(m, net),
           "lat": None if enc.last is None else enc.last.detach().to("cpu").clone()}
    del net, s
    return out


def f64_reference(m, batch, lat, t, z):
    """CPU float64: LOUDAR's FM.loss_fn on a float64 copy of the network, the same t, noise and shared latents; the
    rotary frequency buffer stays float32 (LOUDAR computes rotary angles in float32). -> {loss, grads, norm} or
    {"error"}."""
    import contextlib
    import copy
    import io

    torch, dp, FM = m["torch"], m["dp"], m["FM"]
    net = copy.deepcopy(m["base"]).double()
    kept32 = []
    for name, mod in net.named_modules():
        if "inv_freq" in mod._buffers and mod._buffers["inv_freq"] is not None:
            mod._buffers["inv_freq"] = mod._buffers["inv_freq"].float()
            kept32.append(f"{name}.inv_freq")
    prev = torch.get_default_dtype()
    saved = {k: dp.__dict__.get(k) for k in ("encode", "sample_time_training")}
    try:
        torch.set_default_dtype(torch.float64)
        dp.encode = lambda x: lat.double()
        dp.sample_time_training = lambda n: t.double()
        with contextlib.redirect_stdout(io.StringIO()):
            err, _ = FM.loss_fn(dp, net, batch.double(), n=z.double())
            loss = err.mean(dim=1).mean()
            loss.backward()
        grads = {n: (None if p.grad is None else p.grad.detach().clone()) for n, p in net.named_parameters()}
        return {"loss": float(loss), "grads": grads, "norm": total_norm(m, grads), "kept_float32": kept32}
    except Exception as e:      # noqa: BLE001 (no float64 reference: nothing is calibrated)
        return {"error": f"{type(e).__name__}: {str(e)[:400]}"}
    finally:
        torch.set_default_dtype(prev)
        for k, v in saved.items():
            dp.__dict__.pop(k, None)
            if v is not None:
                dp.__dict__[k] = v
        del net


def compare_runs(m, dev_r, cpu_r, ref):
    """The loss, gradients before the clip, and the clip (norm, non-finite, after) of an MPS run against the CPU's."""
    torch = m["torch"]
    g64 = ref.get("grads") if "error" not in ref else None
    draws = bool(torch.equal(dev_r["t"], cpu_r["t"]) and torch.equal(dev_r["z"], cpu_r["z"]))
    pre_rows = norms_rows(m, dev_r["pre"], cpu_r["pre"], g64)
    holds = reference_holds(cpu_r["loss"], ref.get("loss") if g64 else None, pre_rows, draws)
    ok = holds["holds"]                            # a calibrated pass only on a reference that itself holds (fix 2)
    loss = scalar_check(dev_r["loss"], cpu_r["loss"], TOL["loss"], f64=ref.get("loss") if g64 else None, ref_ok=ok)
    grads = tensor_check(pre_rows, TOL["grad"], ref_ok=ok)
    post64 = None
    if g64:
        coef = min(1.0, MAX_NORM / (ref["norm"] + 1e-6))
        post64 = {k: (None if v is None else v * coef) for k, v in g64.items()}
    nonfin = sum(int((~torch.isfinite(v)).sum()) for v in dev_r["post"].values() if v is not None)
    nonfin += 0 if math.isfinite(dev_r["norm"]) else 1
    after = tensor_check(norms_rows(m, dev_r["post"], cpu_r["post"], post64), TOL["clip_after"], ref_ok=ok)
    clip = clip_check(dev_r["norm"], cpu_r["norm"], nonfin, after, f64_norm=ref.get("norm") if g64 else None,
                      ref_ok=ok)
    return {"loss": loss, "grads": grads, "clip": clip, "same_draws": draws, "reference": holds,
            "calibration": "allowed" if ok else f"refused, direct checks only: {'; '.join(holds['why'])}",
            "pass_network": bool(loss["pass"] and grads["pass"]), "pass_clip": bool(clip["pass"])}


def optimizer_ema_check(m, grads):
    """AdamW's step and the EMA update on MPS against the CPU's, from identical gradients and weights (amendment 2),
    calibrated against CPU float64. -> {"adamw", "ema": {it: row}, "pass"}."""
    import copy

    torch, T = m["torch"], m["T"]
    base = {n: p.detach().clone() for n, p in m["base"].named_parameters()}

    def adam(dev, dtype):
        net = copy.deepcopy(m["base"]).to(dev, dtype)
        for n, p in net.named_parameters():
            g = grads.get(n)
            p.grad = None if g is None else g.to(dev, dtype)
        opt = m["hydra"].utils.instantiate(m["args"].exp.optimizer, params=net.parameters())
        opt.step()
        sync(m, dev)
        return {n: (p.detach().to("cpu") - base[n].to(dtype)) for n, p in net.named_parameters()}, \
            {n: p.detach().to("cpu", torch.float32).clone() for n, p in net.named_parameters()}
    d_cpu, stepped = adam("cpu", torch.float32)
    d_mps, _ = adam("mps", torch.float32)
    d_64, _ = adam("cpu", torch.float64)
    out = {"adamw": tensor_check(norms_rows(m, d_mps, d_cpu, d_64), TOL["adamw"]), "ema": {}}

    def ema(dev, dtype, it):
        import types

        net = copy.deepcopy(m["base"]).to(dev, dtype)
        net.load_state_dict({n: v.to(dtype) for n, v in stepped.items()}, strict=False)
        e = copy.deepcopy(m["base"]).to(dev, dtype).eval().requires_grad_(False)
        s = types.SimpleNamespace(args=m["args"], network=net, ema=e, it=it)
        T.Trainer.update_ema(s)
        sync(m, dev)
        return {n: (p.detach().to("cpu") - base[n].to(dtype)) for n, p in e.named_parameters()}
    for it in EMA_ITS:
        out["ema"][str(it)] = tensor_check(norms_rows(m, ema("mps", torch.float32, it), ema("cpu", torch.float32, it),
                                                      ema("cpu", torch.float64, it)), TOL["ema"])
    out["pass"] = bool(out["adamw"]["pass"] and all(r["pass"] for r in out["ema"].values()))
    return out


def five_steps(m, enc, dev, xs, enc_mode, clip_mode):
    """Five steps on `dev` from the released weights, seeded per step: losses, clip norms, seconds, non-finite steps,
    the weight change. -> the row (tensors dropped but the change)."""
    import copy
    import time as _t

    torch, rec = m["torch"], m["rec"]
    net = copy.deepcopy(m["base"]).to(dev)
    w0 = {n: p.detach().to("cpu").clone() for n, p in net.named_parameters()}
    s = stub(m, net, dev, cycled(m, xs, dev))
    enc.use(enc_mode, dev)
    rec.clip_mode = clip_mode if dev == "mps" else "native"
    losses, norms, secs, bad = [], [], [], 0
    for k in range(FIVE):
        torch.manual_seed(FIVE_SEED + k)
        rec.reset()
        sync(m, dev)
        t0 = _t.perf_counter()
        one_step(m, s)
        sync(m, dev)
        secs.append(_t.perf_counter() - t0)
        loss, norm = float(rec.error.mean(dim=1).mean()), float(rec.norm)
        losses.append(loss)
        norms.append(norm)
        bad += nonfinite_step(loss, norm, params_finite(m, net))
    delta = {n: p.detach().to("cpu") - w0[n] for n, p in net.named_parameters()}
    del net, s
    return {"losses": losses, "clip_norms": norms, "seconds": secs, "nonfinite": bad, "delta": delta}


def run_two(m, enc, batch, enc_ok, clip_mode, train=None, reference=None, compare=None):
    """Run 2, end to end (the review of #666, fix 1). The encoder is the one its own latent check chose (`enc_ok`:
    LOUDAR's MPS encoder, else the CPU fallback); a failure here never switches it. The MPS step is compared against
    the CPU network fed that MPS run's own latents (shared), with the float64 reference built on the same latents.
    train/reference/compare default to train_once/f64_reference/compare_runs (a test passes fakes).
    -> (record, encoder mode or None, fallbacks, cpu_only)."""
    train = train or train_once
    reference = reference or f64_reference
    compare = compare or compare_runs
    enc_mode = "mps" if enc_ok else "cpu"
    fallbacks = [] if enc_ok else [FALLBACK_NAMES[("encoder", "cpu")]]
    r, err = guarded(lambda: train(m, enc, "mps", batch, enc_mode, clip_mode))
    if err:
        return ({"encoder": enc_mode, "error": err}, None, fallbacks,
                [f"run 2 ({enc_mode} encoder): {'MPS out of memory' if err['kind'] == 'oom' else 'unsupported op'}: "
                 f"{err['op'] or err['error']}"])
    lat = r["lat"]
    cpu = train(m, enc, "cpu", batch, "cpu", "native", shared=lat)
    ref = reference(m, batch, lat, cpu["t"], cpu["z"])
    c = compare(m, r, cpu, ref)
    rec = dict(c, encoder=enc_mode, latents="the MPS run's own, shared with the CPU network",
               float64_reference={k: v for k, v in ref.items() if k != "grads"})
    if not (c["pass_network"] and c["pass_clip"]):
        return rec, None, fallbacks, [f"run 2: end to end does not match on MPS ({enc_mode} encoder)"]
    return rec, enc_mode, fallbacks, []


def cmd_check(a):
    """The gradient check, the fallbacks and the five steps -> PP_DIR/check.json (only JSON)."""
    require_on_main()
    before = machine_state()
    if before["torch"]:
        raise SystemExit(f"another torch or MPS process runs ({before['pids']['torch']}): never two MPS jobs")
    if before["render"]:
        raise SystemExit("renders are running: check competes for the CPU's performance cores; run it when they end")
    d = probe_dir(a.data_dir)
    if (d / "check.json").exists():
        raise SystemExit(f"{d / 'check.json'} exists: never overwritten")
    try:
        m = setup(a)
    except Anomaly as e:                           # a pin or hash failed: nothing of LOUDAR's ran
        write_json(d / "check.json", dict(e.record, plan=PLAN, ledger=f"{LEDGER_ID} {KEY}", machine_before=before,
                                          anomaly=e.reasons, cpu_only=[], fallbacks=[], provisional="PP-anomaly",
                                          config={"encoder": None, "clip": None},
                                          time=time.strftime("%Y-%m-%d %H:%M:%S")))
        raise SystemExit(f"PP-anomaly: {e.reasons}")
    torch = m["torch"]
    import copy

    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {KEY}", "machine_before": before, "tolerances": TOL,
           "calibration_multiple": CALIB_MULT, "per_tensor_floor": PER_TENSOR_FLOOR, "seed": CHECK_SEED,
           "checkpoint": m["checkpoint"], "file_sha256": m["file_sha256"], "func_sha256": m["func_sha256"],
           "prep_sha256": m["prep_sha256"], "versions": LR.versions(), "threads": THREADS,
           "network_training_mode": bool(m["base"].training), "placeholders": list(PLACEHOLDER_MODULES),
           "env": {k: os.environ.get(k) for k in list(LR.ENV) + ["HF_HOME", "PYTORCH_ENABLE_MPS_FALLBACK"]}}
    anomaly, cpu_only, fallbacks = list(m["anomaly"]), [], []
    if anomaly:                                    # a running function or the samples are not the pinned: nothing runs
        res.update({"anomaly": anomaly, "cpu_only": [], "fallbacks": [], "config": {"encoder": None, "clip": None},
                    "provisional": "PP-anomaly", "file_events": m["audit"].events,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        write_json(d / "check.json", res)
        raise SystemExit(f"PP-anomaly: {anomaly}")
    xs = normalised(m)
    batch = torch.stack([xs[i] for i in batch_indices(0)])
    ae_cpu = m["dp"].autoencoder
    ae_mps = copy.deepcopy(ae_cpu).to("mps")
    enc = Encoder(m, ae_cpu, ae_mps)

    # the encoder forward
    with torch.no_grad():
        enc.use("cpu", "cpu")
        lat_cpu = m["dp"].transform_fwd(batch).detach().to("cpu")
        enc.use("mps", "mps")
        lat_mps, err = guarded(lambda: m["dp"].transform_fwd(batch.to("mps")).detach().to("cpu"))
    lat64 = None
    try:
        ae64 = copy.deepcopy(ae_cpu).double()
        m["dp"].autoencoder = ae64
        m["dp"].__dict__.pop("encode", None)
        m["dp"].encode = enc.orig
        with torch.no_grad():
            lat64 = m["dp"].transform_fwd(batch.double()).detach()
    except Exception as e:      # noqa: BLE001 (no float64 encoder: the encoder is not calibrated)
        res["encoder_f64_error"] = f"{type(e).__name__}: {str(e)[:300]}"
    if err:
        res["encoder"] = {"mps": {"pass": False, "error": err}}
        enc_ok = False
        if err["kind"] == "oom":
            cpu_only.append(f"MPS out of memory in the encoder: {err['error']}")
    else:
        dn = float(torch.linalg.vector_norm(lat_mps.double() - lat_cpu.double()))
        rn = float(torch.linalg.vector_norm(lat_cpu.double()))
        f64 = None
        if lat64 is not None:
            r64 = float(torch.linalg.vector_norm(lat64))
            f64 = {"dev": float(torch.linalg.vector_norm(lat_mps.double() - lat64)) / r64,
                   "cpu": float(torch.linalg.vector_norm(lat_cpu.double() - lat64)) / r64}
        res["encoder"] = {"mps": dict(encoder_verdict(rel(dn, rn), f64), shape=list(lat_cpu.shape))}
        enc_ok = bool(res["encoder"]["mps"]["pass"])
    if not enc_ok:
        res["encoder"]["cpu"] = {"pass": True, "note": "the CPU encoder's latents are the reference by construction"}

    # run 1: the network alone on shared CPU latents; the clip's fallbacks in order
    cpu1 = train_once(m, enc, "cpu", batch, "cpu", "native", shared=lat_cpu)
    ref = f64_reference(m, batch, lat_cpu, cpu1["t"], cpu1["z"])
    res["float64_reference"] = {k: v for k, v in ref.items() if k != "grads"}
    res["cpu_run1"] = {"loss": cpu1["loss"], "norm": cpu1["norm"], "finite": cpu1["finite"]}
    res["run1"] = {}
    clip_mode = None
    for mode in (CLIP_MODES if not cpu_only else ()):
        r, err = guarded(lambda: train_once(m, enc, "mps", batch, "cpu", mode, shared=lat_cpu))
        if err:
            res["run1"][mode] = {"error": err}
            if err["kind"] == "oom" or m["rec"].clip_error is None:
                cpu_only.append(f"run 1 ({mode}): {'MPS out of memory' if err['kind'] == 'oom' else 'unsupported op'}"
                                f" outside the clip: {err['op'] or err['error']}")
                break
            continue                                   # an unsupported op in the clip: its fallback next
        c = compare_runs(m, r, cpu1, ref)
        res["run1"][mode] = c
        if not c["same_draws"]:
            raise SystemExit("t or the noise differ between the devices: stop (to the orchestrator)")
        if not c["pass_network"]:
            cpu_only.append("run 1: MPS loss or gradients before the clip do not match the CPU's")
            break
        if c["pass_clip"]:
            clip_mode = mode
            break
    if clip_mode is None and not cpu_only:
        cpu_only.append("the clip does not match on MPS with any declared fallback")
    if clip_mode and clip_mode != "native":
        fallbacks.append(FALLBACK_NAMES[("clip", clip_mode)])

    # run 2: end to end, the MPS step with the encoder the latent check chose (fix 1: the encoder is judged only by
    # its own latent check), against the CPU network fed that MPS run's own latents, with a float64 reference built
    # on those same latents
    res["run2"], enc_mode = {}, None
    if not cpu_only:
        res["run2"], enc_mode, fb, co = run_two(m, enc, batch, enc_ok, clip_mode)
        fallbacks += fb
        cpu_only += co

    # AdamW and the EMA from identical gradients
    if not cpu_only:
        r, err = guarded(lambda: optimizer_ema_check(m, cpu1["post"]))
        res["optimizer_ema"] = r if r else {"error": err}
        if err:
            cpu_only.append(f"AdamW or the EMA on MPS: {err['op'] or err['error']}")
        elif not r["pass"]:
            cpu_only.append("AdamW's step or the EMA update on MPS does not match the CPU's")

    # five steps on each device

    five_cpu = five_steps(m, enc, "cpu", xs, "cpu", "native")
    res["five"] = {"cpu": {k: v for k, v in five_cpu.items() if k != "delta"},
                   "cpu_rate": cpu_rate(five_cpu["seconds"])}
    nonfinite = 0
    if not cpu_only:
        r, err = guarded(lambda: five_steps(m, enc, "mps", xs, enc_mode, clip_mode))
        if err:
            res["five"]["mps"] = {"error": err}
            cpu_only.append(f"five steps on MPS: {err['op'] or err['error']}")
        else:
            res["five"]["mps"] = {k: v for k, v in r.items() if k != "delta"}
            res["five"]["weight_change"] = tensor_check(norms_rows(m, r["delta"], five_cpu["delta"]), float("inf"))
            nonfinite = r["nonfinite"]
    anomaly += m["audit"].anomalies()
    files = [str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()]
    anomaly += [f"{f}: not JSON and not a prep segment" for f in probe_files_refusal(files, m["seg_names"])]
    res.update({"config": {"encoder": enc_mode, "clip": clip_mode}, "fallbacks": fallbacks, "cpu_only": cpu_only,
                "anomaly": anomaly, "nonfinite_mps_five": nonfinite, "file_events": m["audit"].events,
                "provisional": pp_code(anomaly, cpu_only, nonfinite, fallbacks)[0],
                "peak_rss_bytes": peak_rss(), "mps_driver_bytes": torch.mps.driver_allocated_memory(),
                "machine_after": machine_state(), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    write_json(d / "check.json", res)
    print(f"PRIOR CHECK DONE: config {res['config']}, provisional {res['provisional']}; fallbacks {fallbacks}; "
          f"cpu-only {cpu_only}; anomaly {anomaly}")


def peak_rss():
    import resource

    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r if sys.platform == "darwin" else r * 1024)


def timed_block(m, enc, xs, steps, warmup, cfg, label):
    """One timed block on MPS: `steps` steps from the released weights, it from TIMED_IT0, a sync before each clock
    read; per-step seconds, losses, norms, non-finite steps, memory; idle at both ends. -> the row."""
    import copy
    import time as _t

    torch, rec = m["torch"], m["rec"]
    start = machine_state()
    net = copy.deepcopy(m["base"]).to("mps")
    s = stub(m, net, "mps", cycled(m, xs, "mps"), it=TIMED_IT0)
    enc.use(cfg["encoder"], "mps")
    rec.clip_mode = cfg["clip"]
    torch.manual_seed(TIME_SEED)
    secs, losses, norms, bad, drv, cur = [], [], [], [], 0, 0
    err = None
    for k in range(steps):
        rec.reset()
        sync(m, "mps")
        t0 = _t.perf_counter()
        _, err = guarded(lambda: one_step(m, s))
        sync(m, "mps")
        if err:
            break
        secs.append(_t.perf_counter() - t0)
        loss, norm = float(rec.error.mean(dim=1).mean()), float(rec.norm)
        losses.append(loss)
        norms.append(norm)
        if nonfinite_step(loss, norm, params_finite(m, net)):
            bad.append(k + 1)
        drv = max(drv, torch.mps.driver_allocated_memory())
        cur = max(cur, torch.mps.current_allocated_memory())
    end = machine_state()
    del net, s
    torch.mps.empty_cache()
    return {"label": label, "samples": int(xs[0].shape[-1]), "steps": steps, "warmup": warmup, "done": len(secs),
            "error": err, "seconds": secs, "losses": losses, "clip_norms": norms, "nonfinite_steps": bad,
            "rate": block_rate(secs, warmup), "mps_driver_peak_bytes": drv, "mps_current_peak_bytes": cur,
            "machine_start": start, "machine_end": end, "idle": bool(start["idle"] and end["idle"])}


def encode_block(m, enc, xs, cfg, n=ENCODE_BLOCK, warmup=ENCODE_WARMUP):
    """The encode-only block: the configured encoder on a step's batch under no_grad, a sync before each clock read."""
    import time as _t

    torch = m["torch"]
    start = machine_state()
    enc.use(cfg["encoder"], "mps")
    secs = []
    with torch.no_grad():
        for k in range(n):
            b = batch_of(m, xs, k, "mps")
            sync(m, "mps")
            t0 = _t.perf_counter()
            m["dp"].transform_fwd(b)
            sync(m, "mps")
            secs.append(_t.perf_counter() - t0)
    end = machine_state()
    return {"samples": int(xs[0].shape[-1]), "n": n, "warmup": warmup, "seconds": secs,
            "rate": block_rate(secs, warmup), "machine_start": start, "machine_end": end,
            "idle": bool(start["idle"] and end["idle"])}


def time_run(a, check):
    """The timed blocks on MPS with the configuration the check passed (fallbacks included). -> the record."""
    import copy

    cfg = check["config"]
    try:
        m = setup(a)
    except Anomaly as e:                           # a pin or hash failed: nothing of LOUDAR's ran
        return dict(e.record, plan=PLAN, ledger=f"{LEDGER_ID} {KEY}", config=cfg, check_sha256=a.check_sha256,
                    blocks={}, encode={}, split={}, anomaly=e.reasons, time=time.strftime("%Y-%m-%d %H:%M:%S"))
    rec = {"plan": PLAN, "ledger": f"{LEDGER_ID} {KEY}", "config": cfg, "check_sha256": a.check_sha256,
           "checkpoint": m["checkpoint"], "file_sha256": m["file_sha256"], "func_sha256": m["func_sha256"],
           "prep_sha256": m["prep_sha256"], "versions": LR.versions(), "threads": THREADS, "seed": TIME_SEED,
           "it": {"start": TIMED_IT0, "ema_branch": "ramp-up (it x batch_size < ema_rampup for it < 5,000), as "
                                                    "training_loop starts at it = 0"},
           "rate_note": RATE_NOTE, "blocks": {}, "encode": {}, "split": {}}
    if m["anomaly"]:                               # a pin or hash failed: nothing runs
        return dict(rec, anomaly=list(m["anomaly"]), file_events=m["audit"].events,
                    time=time.strftime("%Y-%m-%d %H:%M:%S"))
    ae_mps = copy.deepcopy(m["dp"].autoencoder).to("mps") if cfg["encoder"] == "mps" else None
    enc = Encoder(m, m["dp"].autoencoder, ae_mps)
    xs = normalised(m)
    xs_short = normalised(m, SEG_SHORT)
    for label, x, steps, warm in (("long", xs, a.steps, WARMUP), ("short", xs_short, SHORT_STEPS, SHORT_WARMUP)):
        b = rec["blocks"][label] = timed_block(m, enc, x, steps, warm, cfg, label)
        if b["error"]:
            break
        e = rec["encode"][label] = encode_block(m, enc, x, cfg)
        rec["split"][label] = split_rate(b["rate"]["mean_s"], e["rate"]["mean_s"])
    anomaly = m["audit"].anomalies()
    d = m["dir"]
    files = [str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()]
    anomaly += [f"{f}: not JSON and not a prep segment" for f in probe_files_refusal(files, m["seg_names"])]
    return dict(rec, peak_rss_bytes=peak_rss(), memsize_bytes=memsize(), anomaly=anomaly,
                file_events=m["audit"].events, time=time.strftime("%Y-%m-%d %H:%M:%S"))


def memsize():
    r = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
    return int(r.stdout.strip()) if r.stdout.strip().isdigit() else None


def check_refusal(check):
    """(Pure.) Why `time` may not run on a check record, or None: the check must have chosen a configuration (no
    anomaly, nothing cpu-only)."""
    if not isinstance(check, dict):
        return "no check.json: run check first"
    if check.get("anomaly"):
        return f"the check found an anomaly ({check['anomaly']}): stop (PP-anomaly)"
    if check.get("cpu_only"):
        return f"the check reads cpu-only ({check['cpu_only']}): no MPS timing"
    cfg = check.get("config") or {}
    if cfg.get("encoder") not in ENCODER_MODES or cfg.get("clip") not in CLIP_MODES:
        return f"the check chose no configuration ({cfg})"
    return None


def cmd_time(a, runner=None):
    """The timed blocks -> PP_DIR/time-<stamp>.json. Only JSON is written."""
    require_on_main()
    before = machine_state()
    if before["torch"]:
        raise SystemExit(f"another torch or MPS process runs ({before['pids']['torch']}): never two MPS jobs")
    d = probe_dir(a.data_dir)
    cp = d / "check.json"
    check = json.loads(cp.read_text()) if cp.exists() else None
    why = check_refusal(check)
    if why:
        raise SystemExit(why)
    a.check_sha256 = file_sha(cp)
    out = d / f"time-{time.strftime('%Y%m%d-%H%M%S')}.json"
    rec = (runner or time_run)(a, check)
    rec["machine_before"], rec["check_sha256"] = before, a.check_sha256
    write_json(out, rec)
    lg = (rec.get("blocks") or {}).get("long")
    if not lg:
        print(f"PRIOR TIME STOPPED: {out.name}: anomaly {rec.get('anomaly')}")
        return
    print(f"PRIOR TIME DONE: {out.name}: long {lg['done']}/{lg['steps']} steps, rate {lg['rate']['rate']}, "
          f"idle {lg['idle']}, non-finite {len(lg['nonfinite_steps'])}, error {lg['error']}, anomaly {rec['anomaly']}")


# --- read ---------------------------------------------------------------------------------------------------------------

def quoted_block(times):
    """(Pure.) The block the rate is quoted from: the first time record (by name) whose 526,080-sample block ran all
    its steps and was idle at both ends. times: [(name, record)]. -> (name, record) or None."""
    for name, r in sorted(times, key=lambda x: x[0]):
        b = ((r.get("blocks") or {}).get("long")) or {}
        if b.get("idle") and b.get("done") == b.get("steps") == STEPS and not b.get("error") and \
                b.get("samples") == SEG:
            return name, r
    return None


def reading(check, times):
    """(Pure.) The probe's reading from check.json and the time records: the PP code (`pp_code`), the quoted idle
    block's rate and projections, the encode split, memory, the gradient table and the non-finite count (the five MPS
    steps and every timed step). -> the record, or raises when no idle block exists and the check ran on MPS."""
    anomaly = list(check.get("anomaly") or [])
    cpu_only = list(check.get("cpu_only") or [])
    fallbacks = list(check.get("fallbacks") or [])
    nonfinite = int(check.get("nonfinite_mps_five") or 0)
    for _, r in times:
        anomaly += list(r.get("anomaly") or [])
        for b in (r.get("blocks") or {}).values():
            nonfinite += len(b.get("nonfinite_steps") or [])
            e = b.get("error")
            if e:
                cpu_only.append(f"time ({b.get('label')}): {'MPS out of memory' if e.get('kind') == 'oom' else 'an '
                                'unsupported op'}: {e.get('op') or e.get('error')}")
    q = quoted_block(times)
    if q is None and not anomaly and not cpu_only:
        raise SystemExit("no idle 526,080-sample block of 200 steps: rerun time when the machine is idle")
    code, why = pp_code(anomaly, cpu_only, nonfinite, fallbacks)
    out = {"code": code, "why": why, "order": list(CODES), "config": check.get("config"), "fallbacks": fallbacks,
           "rate_note": RATE_NOTE,
           "nonfinite_mps_steps": nonfinite, "cpu_rate": (check.get("five") or {}).get("cpu_rate"),
           "cpu_projections": projections((check.get("five") or {}).get("cpu_rate")),
           "gradient_table": {k: check.get(k) for k in ("encoder", "run1", "run2", "optimizer_ema")},
           "check_peak_rss_bytes": check.get("peak_rss_bytes")}
    if q:
        name, r = q
        lg, sh = r["blocks"]["long"], r["blocks"].get("short") or {}
        out.update({"quoted": name, "rate": lg["rate"], "projections": projections(lg["rate"]["rate"]),
                    "split": r.get("split"), "short": {"samples": sh.get("samples"), "rate": sh.get("rate"),
                                                       "idle": sh.get("idle"),
                                                       "projections": projections((sh.get("rate") or {}).get("rate"),
                                                                                  seg=sh.get("samples") or SEG_SHORT)},
                    "memory": {"peak_rss_bytes": r.get("peak_rss_bytes"),
                               "mps_driver_peak_bytes": lg.get("mps_driver_peak_bytes"),
                               "mps_current_peak_bytes": lg.get("mps_current_peak_bytes"),
                               "memsize_bytes": r.get("memsize_bytes")},
                    "blocks_labelled": {n: {k: b.get("idle") for k, b in (t.get("blocks") or {}).items()}
                                        for n, t in times}})
    return out


def cmd_read(a):
    """The reading -> PP_DIR/outcome.json and a summary for the outcome key (tags only)."""
    require_on_main()
    d = probe_dir(a.data_dir)
    check = json.loads((d / "check.json").read_text())
    times = [(p.name, json.loads(p.read_text())) for p in sorted(d.glob("time-*.json"))]
    out = reading(check, times)
    prep = json.loads((d / "prep.json").read_text())
    hours = json.loads((d / "hours.json").read_text())
    seg_names = [s["name"] for s in prep["segments"]]
    files = [str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()]
    bad = probe_files_refusal(files, seg_names)
    if bad and out["code"] != "PP-anomaly":
        out["code"], out["why"] = "PP-anomaly", [f"{f}: not JSON and not a prep segment" for f in bad]
    out.update({"segments": [s["tag"] for s in prep["segments"]], "prep_sha256": file_sha(d / "prep.json"),
                "hours": {"library": hours["library"]["hours"], "by_source": hours["library"]["by_source"],
                          "excluded": {k: v["hours"] for k, v in hours["library"]["excluded"].items()},
                          "egdb": hours["egdb"]["hours"], "egfxset": hours["egfxset"]["hours"],
                          "goat": hours["goat"]["hours"], "goat_items": hours["goat"]["items"]},
                "hours_sha256": file_sha(d / "hours.json"), "check_sha256": file_sha(d / "check.json"),
                "terms": TERMS, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    write_json(d / "outcome.json", out)
    print(json.dumps({k: out.get(k) for k in ("code", "why", "config", "rate", "projections", "split", "memory",
                                              "nonfinite_mps_steps", "cpu_rate", "hours")}, indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("hours", "prep", "check", "time", "read"):
        p = sub.add_parser(name)
        p.add_argument("--data-dir", default=str(DATA))
        if name in ("hours", "prep"):
            p.add_argument("--dry", action="store_true", help="compute and print; nothing written")
        if name in ("check", "time"):
            p.add_argument("--code", default=CODE_DEFAULT)
            p.add_argument("--models", default=MODELS_DEFAULT)
        if name == "time":
            p.add_argument("--steps", type=int, default=STEPS, choices=(STEPS,))
    a = ap.parse_args(argv)
    {"hours": cmd_hours, "prep": cmd_prep, "check": cmd_check, "time": cmd_time, "read": cmd_read}[a.cmd](a)


if __name__ == "__main__":
    main()
