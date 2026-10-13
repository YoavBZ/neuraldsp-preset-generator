"""pYIN voicing of DI tracks for the part locator's role rule (`docs/part-locator-plan.md`).

Runs in a venv with librosa (the main venv's Python lacks lzma):

    ~/ndsp-presets/tools/rerank-venv/bin/python learn/locator_pyin.py JOBS.json OUT_DIR

JOBS.json: [{"key": ..., "di": path}, ...]. For each job, writes OUT_DIR/<key>.npy, the
per-frame voiced flag (frame 2048, hop 512 at the file's rate resampled to 44.1 kHz).
"""

import json
import multiprocessing
import pathlib
import sys

SR, FRAME, HOP, FMIN, FMAX = 44100, 2048, 512, 70.0, 1400.0


def _one(job):
    import librosa
    import numpy as np
    import soundfile as sf

    out = pathlib.Path(job["out"])
    if out.exists():
        return job["key"]
    x, sr = sf.read(job["di"], always_2d=True, dtype="float32")
    x = x.mean(1)
    if sr != SR:
        x = librosa.resample(x, orig_sr=sr, target_sr=SR)
    _, voiced, _ = librosa.pyin(x, fmin=FMIN, fmax=FMAX, sr=SR, frame_length=FRAME,
                                hop_length=HOP, center=False)
    tmp = out.with_suffix(".tmp.npy")
    np.save(tmp, voiced.astype(bool))
    tmp.rename(out)
    return job["key"]


def main():
    jobs = json.loads(pathlib.Path(sys.argv[1]).read_text())
    out_dir = pathlib.Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    for j in jobs:
        j["out"] = str(out_dir / f"{j['key']}.npy")
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    with multiprocessing.Pool(workers) as pool:
        for i, key in enumerate(pool.imap_unordered(_one, jobs), 1):
            print(f"{i}/{len(jobs)} {key}", flush=True)


if __name__ == "__main__":
    main()
