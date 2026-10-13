"""EG-VAE-lite's E1 data (`docs/egvae-lite-plan.md`, "E1 after review", item 2): C′'s own
training and validation clips, each made once with C′'s `make_clip` and stored as DAC 44 kHz
codes (recording and average-balance DI target, 9 codebooks each).

    $LEARN_PY -m learn.egvae_e1_data index      # clip list + checks -> e1-codes/index.json
    $LEARN_PY -m learn.egvae_e1_data produce    # audio shards (float32, 44.1 kHz) for the encoder
    $DAC_PY   learn/egvae_e1_dac.py encode DIR  # shards -> codes (MPS), deletes each audio shard
    $DAC_PY   learn/egvae_e1_dac.py check DIR   # MPS against CPU `compress` on 3 clips

($LEARN_PY = ~/ndsp-presets/tools/learn-venv/bin/python; $DAC_PY = the DAC venv, which can't
import `learn`, so the two halves meet only through files under DIR.)

**The clips are exactly C′'s** (`direc.fit` with `--cache cache --extra-cache cache-sw50r
cache-ac20 --fold 2`): PR12 rows from `cache`'s memmaps, then SW50R and AC20 read straight
from their pairs FLACs. The pairs' index rows, filtered to lufs ≥ −40 and sorted by id, must
equal `cache-{sw50r,ac20}/meta.json` row for row, so the stored DI spectra (`di_spectrum.npy`)
line up for the target; `index` checks that, and that the DI spectrum recomputed from the FLAC
reproduces the stored one on sample rows. The global row order and the
fold split (K3 fold 2 = validation) are `fit`'s.

**Per clip:** `direc.make_clip` once, with its own rng `default_rng(seed)`, seed = the global
row index (+ 1,000,000 × pass); training clips get C′'s augmentation (`train=True`) and
validation clips none, as in `fit`'s validation. The FULL 6-s recording and the full 6-s
average-balance target are kept, not C′'s 3-s crop: codes are tiny, and random 3-s crops can be
taken later in code space (the crop start `make_clip` drew is recorded but not applied). Both
go 48 → 44.1 kHz (`resample_poly` 147/160). The encoder sets each to −16 LUFS exactly as DAC's
`compress` does (audiotools loudness on the CPU, then `ensure_max_of_audio`), as in E0.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import direc as D  # noqa: E402

DIREC = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc"))
OUT = DIREC / "e1-codes"
FOLD = 2
SHARD = 128                     # clips per shard
MAX_PENDING = 6                 # audio shards waiting for the encoder (about 270 MB each)
SOURCES = (("pr12", "cache", None), ("sw50r", "cache-sw50r", "pairs-sw50r"),
           ("ac20", "cache-ac20", "pairs-ac20"))


def pair_rows(pairs):
    """`build_pair_cache`'s row list, verbatim."""
    rows = []
    for f in sorted(pairs.glob("index-w*.jsonl")):
        rows += [json.loads(line) for line in f.read_text().splitlines() if line]
    rows.sort(key=lambda r: r["id"])
    return [r for r in rows if r["lufs"] >= -40]


def pair_int16(pairs, rid):
    """A pair's recording and DI as `build_pair_cache` stores them (int16, CLIP long)."""
    import numpy as np
    import soundfile as sf

    out = []
    for kind in ("out", "di"):
        a, _ = sf.read(str(pairs / f"{rid}-{kind}.flac"), dtype="float32")
        z = np.zeros(D.CLIP, np.int16)
        z[:len(a)] = np.clip(a * 32767, -32767, 32767)
        out.append(z)
    return out


def build_index(passes=1):
    import numpy as np
    import soundfile as sf

    from learn import train as TR
    from learn.di_robustness import smoothed_spectrum

    fold_of, _ = TR.k3_folds()
    clips, checks = [], {}
    for name, cache, pairs in SOURCES:
        meta = json.loads((DIREC / cache / "meta.json").read_text())
        if pairs:
            rows = pair_rows(DIREC / pairs)
            assert rows == meta, f"{pairs} rows differ from {cache}/meta.json"
            # the DI spectrum, as `build_pair_cache` computed it, reproduces the stored one
            S = np.load(DIREC / cache / "di_spectrum.npy", mmap_mode="r")
            worst = 0.0
            for j in (0, len(rows) // 2, len(rows) - 1):
                y, _ = sf.read(str(DIREC / pairs / f"{rows[j]['id']}-di.flac"), dtype="float32")
                worst = max(worst, float(np.abs(smoothed_spectrum(y.astype(np.float64)) - S[j]).max()))
            checks[name] = {"rows": len(rows), "meta_equal": True, "spectrum_max_abs_db": worst}
        else:
            checks[name] = {"rows": len(meta)}
        for j, m in enumerate(meta):
            f = fold_of.get(m["band"], -1)
            clips.append({"source": name, "row": j, "id": m["id"], "band": m["band"], "fold": f})
    # the order `fit` uses: cache, then each extra cache, rows in order
    n = len(clips)
    entries = []
    for p in range(passes):
        for g, c in enumerate(clips):
            if p and c["fold"] == FOLD:
                continue                # validation is encoded once, unaugmented
            entries.append({**c, "g": g, "pass": p, "seed": g + 1_000_000 * p,
                            "train": c["fold"] != FOLD})
    for k, e in enumerate(entries):
        e["shard"], e["slot"] = divmod(k, SHARD)
    folds = {}
    for c in clips:
        folds[c["fold"]] = folds.get(c["fold"], 0) + 1
    OUT.mkdir(parents=True, exist_ok=True)
    idx = {"plan": "docs/egvae-lite-plan.md, E1 after review",
           "fold_validation": FOLD, "clips": n, "entries": len(entries), "shard_size": SHARD,
           "shards": (len(entries) + SHARD - 1) // SHARD, "passes": passes,
           "train": sum(e["train"] for e in entries), "validation": sum(not e["train"] for e in entries),
           "clips_per_fold": {str(k): v for k, v in sorted(folds.items())},
           "checks": checks, "sr_in": D.SR, "sr_dac": 44100, "resample": "resample_poly 147/160",
           "clip_seconds": D.CLIP / D.SR, "loudness": "-16 LUFS as DAC compress (CPU audiotools)",
           "codebooks": 9, "rows": entries}
    tmp = OUT / "index.json.tmp"
    tmp.write_text(json.dumps(idx))
    tmp.replace(OUT / "index.json")
    print(json.dumps({k: v for k, v in idx.items() if k != "rows"}, indent=1))
    return idx


def produce(worker=0, workers=1):
    """Audio shards for the encoder: shard k holds (n, 2, 264600) float32, [:, 0] the
    recording and [:, 1] the target, at 44.1 kHz; with a JSON sidecar. Resumable: a shard
    whose codes or audio already exist is skipped. Waits while MAX_PENDING shards are queued."""
    import numpy as np
    from scipy.signal import resample_poly

    idx = json.loads((OUT / "index.json").read_text())
    rows = idx["rows"]
    audio, codes = OUT / "audio", OUT / "codes"
    audio.mkdir(exist_ok=True)
    codes.mkdir(exist_ok=True)
    mm = {"pr12": (np.load(DIREC / "cache/input.npy", mmap_mode="r"),
                   np.load(DIREC / "cache/di.npy", mmap_mode="r"))}
    S = {name: np.load(DIREC / cache / "di_spectrum.npy", mmap_mode="r") for name, cache, _ in SOURCES}
    pairs = {name: DIREC / p for name, _, p in SOURCES if p}
    avg = D.fold_average(DIREC / "cache", FOLD)
    bleed = D.load_bleed(FOLD)
    print(f"worker {worker}/{workers}: {idx['shards']} shards, bleed {len(bleed)}", flush=True)
    t0, done = time.time(), 0
    for k in range(worker, idx["shards"], workers):
        name = f"shard-{k:05d}"
        if (codes / f"{name}.npz").exists() or (audio / f"{name}.npy").exists():
            continue
        while len(list(audio.glob("shard-*.npy"))) >= MAX_PENDING:
            time.sleep(5)
        part = [e for e in rows[k * idx["shard_size"]:(k + 1) * idx["shard_size"]]]
        buf = np.zeros((len(part), 2, D.CLIP * 147 // 160), np.float32)
        side = []
        for i, e in enumerate(part):
            if e["source"] == "pr12":
                x16, y16 = (np.asarray(a[e["row"]]) for a in mm["pr12"])
            else:
                x16, y16 = pair_int16(pairs[e["source"]], e["id"])
            rng = np.random.default_rng(e["seed"])
            x, y, a = D.make_clip(x16, y16, S[e["source"]][e["row"]], avg, rng, e["train"], bleed)
            buf[i, 0] = resample_poly(x, 147, 160)
            buf[i, 1] = resample_poly(y, 147, 160)
            side.append({"g": e["g"], "pass": e["pass"], "crop_start": int(a)})
        tmp = audio / f"{name}.tmp.npy"
        np.save(tmp, buf)
        (audio / f"{name}.json").write_text(json.dumps(side))
        tmp.replace(audio / f"{name}.npy")
        done += 1
        el = time.time() - t0
        print(f"produced {name} ({len(part)} clips) {el / done:.1f} s/shard", flush=True)
    print(f"worker {worker} finished", flush=True)


def status():
    """Shards encoded, and the finish time at the rate of the last 10 shards."""
    idx = json.loads((OUT / "index.json").read_text())
    t = sorted(f.stat().st_mtime for f in (OUT / "codes").glob("shard-?????.npz"))
    left = idx["shards"] - len(t)
    msg = f"{len(t)}/{idx['shards']} shards encoded"
    if len(t) > 2 and left:
        recent = t[-11:]
        rate = (recent[-1] - recent[0]) / (len(recent) - 1)
        msg += f", {rate:.0f} s/shard lately, finish about " + time.strftime(
            "%a %H:%M", time.localtime(time.time() + left * rate))
    print(msg)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "index":
        build_index(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif cmd == "produce":
        produce(*(int(a) for a in sys.argv[2:4]))
    else:
        {"status": status}[cmd]()
