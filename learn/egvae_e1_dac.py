"""E1's DAC half (`docs/egvae-lite-plan.md`, "E1 after review"; data side in
`learn/egvae_e1_data.py`). Run with the DAC venv, which can't import `learn`.

    $DAC_PY learn/egvae_e1_dac.py encode DIR [DEVICE]   # DIR/audio/shard-k.npy -> DIR/codes/shard-k.npz
                                                        # (one MPS and CPU encoders may run together)
    $DAC_PY learn/egvae_e1_dac.py check DIR             # MPS batched against CPU `compress`, 3 clips

Each signal is set to −16 LUFS exactly as DAC 1.0.0's `compress` does when unchunked
(`win_duration=None`, as in E0): audiotools loudness on the CPU, `normalize(-16)`,
`ensure_max_of_audio()`, then `preprocess` (right-pad to a multiple of the 512 hop) and
`encode` with all 9 codebooks, padding on, eval mode, no gradients. Signals are batched on the
encoder (a batch item doesn't see the others). A codes shard holds `x` and `y` (n, 9, frames)
int16 codes for the recording and the target, and `x_db`/`y_db`, the loudness before
normalising. The audio shard is deleted once its codes are written. Resumable; several
encoders share the shards by claiming each with a lock file (a lock whose process is gone is
taken over). The MPS and CPU paths give the same codes (`check`).
"""

import json
import os
import pathlib
import sys
import time

import numpy as np
import torch

SR44 = 44100
NORM_DB = -16
BATCH = 16


def load_model(device):
    import dac

    torch.set_grad_enabled(False)
    m = dac.DAC.load(dac.utils.download(model_type="44khz")).eval().to(device)
    m.padding = True                   # as compress sets it for an unchunked window
    return m


def normalise(a):
    """(n, T) float32 at 44.1 kHz -> (n, 1, T) tensor at −16 LUFS as `compress` does, plus
    the loudness before normalising."""
    from audiotools import AudioSignal

    sig = AudioSignal(torch.from_numpy(np.ascontiguousarray(a))[:, None], SR44)
    db = sig.loudness().clone()
    sig.normalize(NORM_DB)
    sig.ensure_max_of_audio()
    return sig.audio_data, db


def encode(model, audio, device):
    out = []
    for s in range(0, len(audio), BATCH):
        x = model.preprocess(audio[s:s + BATCH].to(device), SR44)
        _, c, _, _, _ = model.encode(x)
        out.append(c.cpu())
    return torch.cat(out).numpy().astype(np.int16)


def claim(lock):
    """Take a shard: create its lock with this pid; take over a lock whose process is gone."""
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                pid = int(lock.read_text() or 0)
                os.kill(pid, 0)
                return False                    # alive: someone else's
            except (ProcessLookupError, ValueError):
                lock.unlink(missing_ok=True)    # stale
            except FileNotFoundError:
                pass
    return False


def run(root, device="mps"):
    idx = json.loads((root / "index.json").read_text())
    model = load_model(device)
    audio_dir, codes_dir = root / "audio", root / "codes"
    codes_dir.mkdir(exist_ok=True)
    log = open(root / "encode-progress.log", "a")
    t0, done = time.time(), 0
    pending = [k for k in range(idx["shards"]) if not (codes_dir / f"shard-{k:05d}.npz").exists()]
    print(f"{len(pending)} of {idx['shards']} shards to encode on {device}", flush=True)
    for n, k in enumerate(pending):
        name = f"shard-{k:05d}"
        if (codes_dir / f"{name}.npz").exists() or not claim(codes_dir / f"{name}.lock"):
            continue
        src = audio_dir / f"{name}.npy"
        while not src.exists():
            time.sleep(2)
        a = np.load(src)
        side = json.loads((audio_dir / f"{name}.json").read_text())
        res = {}
        for j, key in enumerate(("x", "y")):
            sig, db = normalise(a[:, j])
            res[key] = encode(model, sig, device)
            res[f"{key}_db"] = db.numpy().astype(np.float32)
        res["g"] = np.array([s["g"] for s in side], np.int32)
        res["pass"] = np.array([s["pass"] for s in side], np.int8)
        res["crop_start"] = np.array([s["crop_start"] for s in side], np.int32)
        tmp = codes_dir / f"{name}.tmp.npz"
        np.savez(tmp, **res)
        tmp.replace(codes_dir / f"{name}.npz")
        src.unlink()
        (audio_dir / f"{name}.json").unlink()
        (codes_dir / f"{name}.lock").unlink()
        done += 1
        el = time.time() - t0
        left = idx["shards"] - len(list(codes_dir.glob("shard-?????.npz")))
        msg = (f"{time.strftime('%H:%M:%S')} {device} {name} {res['x'].shape} {el / done:.1f} s/shard "
               f"here, {left} shards left in all")
        print(msg, flush=True)
        log.write(msg + "\n")
        log.flush()
    print("all shards encoded", flush=True)


def check(root, n=3):
    """The first n clips of the first audio shard: MPS batched (this script's path) against
    CPU batched and against CPU `compress(win_duration=None)` one clip at a time (E0's path).
    Per-codebook code agreement -> DIR/mps-check.json."""
    from audiotools import AudioSignal

    a = np.load(sorted((root / "audio").glob("shard-?????.npy"))[0])[:n]
    out = {}
    cpu = load_model("cpu")
    mps = load_model("mps")
    for j, key in enumerate(("x", "y")):
        sig, _ = normalise(a[:, j])
        c_mps = encode(mps, sig, "mps")
        c_cpu = encode(cpu, sig, "cpu")
        c_ref = np.stack([cpu.compress(AudioSignal(torch.from_numpy(a[i, j])[None, None], SR44),
                                       win_duration=None, normalize_db=NORM_DB).codes[0].numpy()
                          for i in range(n)]).astype(np.int16)
        agree = lambda p, q: [round(float((p[:, i] == q[:, i]).mean()), 4) for i in range(9)]  # noqa: E731
        out[key] = {"frames": int(c_mps.shape[-1]),
                    "mps_vs_cpu_per_codebook": agree(c_mps, c_cpu),
                    "cpu_batched_vs_cpu_compress_per_codebook": agree(c_cpu, c_ref),
                    "mps_vs_cpu_compress_per_codebook": agree(c_mps, c_ref)}
        print(key, json.dumps(out[key]), flush=True)
    (root / "mps-check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[2]).expanduser()
    if sys.argv[1] == "encode":
        run(root, *(sys.argv[3:4]))
    else:
        check(root)
