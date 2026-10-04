#!/usr/bin/env python3
"""Record one DI-to-amp-track lag per development part, measured on the panel's renders.

    python scripts/record_part_lags.py --panel-dir ~/ndsp-presets/runs/kill/sw50r \\
        --json docs/validation-lags.json

The catalogue's `lag_ms` (`docs/validation-datasets.json`) comes from 10-ms envelopes,
so it is quantised to 10 ms. Here, on each part's 10-s validation crop:

1. **Candidates.** The summed, normalised 80 Hz-2 kHz cross-correlation of the amp track
   with every render of the part in the panel (`analysis.aligned.estimate_lag`'s
   statistic), within ±15 ms of the catalogued lag less the plugin's latency (±50 ms
   where that is refused; refused there too, the part is ambiguous); every local peak
   at least 0.9 of the highest, at least 0.5 ms from a higher one. A DI with mains buzz
   or a steady pulse makes a comb of near-equal peaks, so the highest alone can be an
   alias.
2. **Choice.** With one candidate, it. With several, the one that lets the judge
   (`aligned_distance`, all frames scored) put the renders closest to the amp track on
   average, over the renders it scores at every candidate. The judge is not
   independent evidence here (every render shares the part's DI and amp track, and it
   prefers a made-up 10-ms alias on a part with one clean peak), so a choice among
   several must be confirmed by the onsets.
3. **Cross-check.** An independent estimate from the raw DI: the 1-4 kHz onset
   envelopes of the DI and the amp track, cross-correlated (`onset_lag`). It is a
   check only where its peak is clear (no other peak, 1 ms or more away, within 0.9
   of it); on the panel's renders it reads within 1 ms of the plugin's latency on
   about 90%.
4. **Stability.** Five random sets of nine renders, each pooled, within 2 ms of the
   choice.

A part is **ambiguous** when the onsets clearly disagree (more than 1 ms away), when
several candidates were found and the onsets do not clearly confirm the choice (or the
judge's choice is split, under two thirds of the renders), or the subsets spread over
0.5 ms; its chosen lag is still recorded, with the evidence.

The lag is expressed DI-to-amp-track by adding the latency back. Held-out parts are
never opened. `lag_samples(part)` in `benchmark_recordings.py` reads the file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

SR = 48000
LATENCY = 52            # Morgan's latency in samples: a render lags its DI by this
NEAR, APART_S = 0.9, 0.0005
SUBSETS, SUBSET_SIZE, SUBSET_WINDOW = 5, 9, int(0.002 * SR)   # ±2 ms of the choice
WIN_SHARE, ONSET_TOLERANCE_MS, SPREAD_MS = 2 / 3, 1.0, 0.5
ONSET_CLEAR = 0.9       # an onset peak is clear when nothing 1 ms or more away reaches this


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", type=pathlib.Path, required=True)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--json", type=pathlib.Path, required=True)
    ap.add_argument("--workers", type=int, default=3)
    return ap


def correlation(ref, renders, centre, span):
    """(lags, the summed normalised |correlation|) over centre ± span samples."""
    import numpy as np

    lags = np.arange(centre - span, centre + span + 1)
    total = np.zeros(len(lags))
    a = ref - ref.mean()
    for render in renders:
        n = min(len(a), len(render))
        x, y = a[:n], render[:n] - render[:n].mean()
        norm = np.linalg.norm(x) * np.linalg.norm(y)
        if not norm:
            continue
        size = 1 << int(np.ceil(np.log2(2 * n)))
        keep = (np.fft.rfftfreq(size, 1 / SR) >= 80) & (np.fft.rfftfreq(size, 1 / SR) <= 2000)
        c = np.abs(np.fft.irfft(np.fft.rfft(x, size) * keep * np.conj(np.fft.rfft(y, size) * keep),
                                size))
        total += c[lags % size] / norm
    return lags, total


def _peaks(total):
    """Indices of the local maxima of `total` (an end counts if above its neighbour)."""
    import numpy as np

    left = np.concatenate([[-np.inf], total[:-1]])
    right = np.concatenate([total[1:], [-np.inf]])
    return np.flatnonzero((total >= left) & (total >= right))


def candidates(lags, total, near=NEAR, apart=int(APART_S * SR)):
    """Local peaks at least `near` of the highest, each at least `apart` samples from a
    higher one, highest first, as (lag, height relative to the highest)."""
    import numpy as np

    peaks = _peaks(total)
    top, kept = total.max(), []
    for i in peaks[np.argsort(-total[peaks])]:
        if total[i] < near * top:
            break
        if all(abs(lags[i] - k) >= apart for k, _ in kept):
            kept.append((int(lags[i]), float(total[i] / top)))
    return kept


def onset_lag(di, ref, centre, span, hop=4, floor_db=40.0):
    """(samples the amp track lags the DI, the runner-up's height relative to the peak)
    from their 1-4 kHz onset envelopes: each signal's band-passed level in dB (floored
    40 dB under its peak), its rises cross-correlated, at a resolution of `hop` samples.
    The runner-up is the highest local peak 1 ms or more away (0 when there is none).
    On the SW50R panel's 1978 renders, whose lag is the plugin's 52 samples, 90% read
    within 1 ms, and the worst is 49 ms off: trust a clear peak only."""
    import numpy as np
    from scipy import signal

    band = signal.butter(2, [1000, 4000], btype="bandpass", fs=SR, output="sos")
    smooth = signal.butter(2, 200, fs=SR, output="sos")

    def rises(x):
        env = np.maximum(signal.sosfilt(smooth, np.abs(signal.sosfilt(band, x))), 0.0)[::hop]
        level = 20 * np.log10(env + 1e-20)
        level = np.maximum(level, level.max() - floor_db)
        d = np.maximum(np.diff(level, prepend=level[0]), 0.0)
        return d - d.mean()

    a, b = rises(ref), rises(di)
    n = min(len(a), len(b))
    size = 1 << int(np.ceil(np.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size)), size)
    lags = np.arange((centre - span) // hop, (centre + span) // hop + 1)
    curve = c[lags % size]
    best = int(np.argmax(curve))
    far = [i for i in _peaks(curve) if abs(lags[i] - lags[best]) * hop >= SR // 1000]
    runner = max((curve[i] for i in far), default=0.0)
    return int(lags[best] * hop), float(runner / curve[best]) if curve[best] > 0 else 1.0


def measure(job):
    part, files, catalogued, crops = job
    import numpy as np
    import soundfile as sf

    from analysis.aligned import aligned_distance

    def mono(path):
        x, rate = sf.read(str(path), dtype="float64")
        if rate != SR:
            raise ValueError(f"{path} is at {rate} Hz, not {SR}")
        return x.mean(axis=1) if x.ndim == 2 else x

    ref, di = mono(crops / part / "reference.wav"), mono(crops / part / "di.wav")
    names = sorted(files)
    renders = [mono(files[n]) for n in names]
    hint = catalogued - LATENCY
    for width_ms in (15, 50):
        span = int(width_ms * SR / 1000)
        lags, total = correlation(ref, renders, hint, 2 * span)
        inside = np.abs(lags - hint) <= span
        refused = bool(total[~inside].max() > total[inside].max())
        if not refused:
            break                                          # its peak is inside the window
    cands = candidates(lags[inside], total[inside])
    evidence = []
    for lag, height in cands:
        d = [aligned_distance(ref, x, di, lag=lag, render_latency=LATENCY, start_s=1.0,
                              end_s=10.0, max_pauses=1.0).distance for x in renders]
        evidence.append({"render_lag": lag, "height": round(height, 4), "distances": d})
    if len(evidence) > 1:
        # Over the renders the judge scores at every candidate, so the means compare
        # like with like; none of them leaves the choice to the correlation's peak.
        common = [i for i in range(len(renders))
                  if all(e["distances"][i] is not None for e in evidence)]
        if common:
            means = [float(np.mean([e["distances"][i] for i in common])) for e in evidence]
            chosen = int(np.argmin(means))
            wins = sum(1 for i in common
                       if min(range(len(evidence)),
                              key=lambda j: evidence[j]["distances"][i]) == chosen)
            for e, m in zip(evidence, means):
                e["mean_distance"] = round(m, 4)
        else:
            chosen, wins = 0, 0
        win_share = wins / len(renders)
    else:
        chosen, win_share = 0, 1.0
    render_lag = evidence[chosen]["render_lag"]
    rng = random.Random(part)                  # the subsets are fixed by the part's name
    subsets = []
    for _ in range(SUBSETS):
        pick = sorted(rng.sample(names, min(SUBSET_SIZE, len(names))))
        sl, st = correlation(ref, [renders[names.index(n)] for n in pick], hint, span)
        near = np.abs(sl - render_lag) <= SUBSET_WINDOW
        subsets.append({"renders": pick, "lag": int(sl[near][np.argmax(st[near])]) + LATENCY})
    spread = (max(s["lag"] for s in subsets) - min(s["lag"] for s in subsets)) / SR * 1000
    onset, runner = onset_lag(di, ref, render_lag + LATENCY, span)
    lag = render_lag + LATENCY
    row = {"lag_samples": lag, "search_ms": width_ms, "search_refused": refused,
           "renders": len(names), "catalogue_lag_samples": catalogued,
           "candidates": [{**e, "lag_samples": e.pop("render_lag") + LATENCY} for e in evidence],
           "judge_win_share": round(win_share, 3),
           "onset_lag_samples": onset, "onset_runner_up": round(runner, 3),
           "subsets": subsets, "subset_spread_ms": round(spread, 3)}
    row.update(classify(len(evidence), win_share, runner, abs(onset - lag) / SR * 1000,
                        spread, refused))
    print(f"{part}: {lag} ({len(evidence)} candidates, judge {win_share:.2f}; onset {onset} "
          f"(runner-up {runner:.2f}); catalogue {catalogued})", flush=True)
    return part, row


def classify(n_candidates, win_share, onset_runner_up, onset_off_ms, spread_ms,
             refused=False):
    """{"onset_clear", "onset_disagrees", "ambiguous"} for one part's evidence: the
    onsets disagree only when their peak is clear and more than 1 ms away; with several
    candidates the choice stands only if the judge's wins reach two thirds and a clear
    onset confirms it."""
    clear = onset_runner_up < ONSET_CLEAR
    disagrees = clear and onset_off_ms > ONSET_TOLERANCE_MS
    unconfirmed = n_candidates > 1 and (win_share < WIN_SHARE or not clear)
    return {"onset_clear": clear, "onset_disagrees": disagrees,
            "ambiguous": bool(refused or disagrees or unconfirmed or spread_ms > SPREAD_MS)}


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    args = build_parser().parse_args()
    from analysis import require

    require("recording part lags")
    from benchmark_recordings import CATALOG

    panel = args.panel_dir.expanduser()
    crops = args.crops_dir.expanduser()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meta = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            meta[slug] = {"split": p.get("split") or s.get("split"),
                          "lag": int(round((p.get("lag_ms") or 0) * SR / 1000))}
    index = json.loads((panel / "index.json").read_text())
    files = {}
    for row in index["rows"]:
        if "file" in row:
            files.setdefault(row["part"], {})[row["candidate"]] = pathlib.Path(row["file"])
    unknown = [p for p in files if p not in meta]
    if unknown:
        die(f"the panel holds parts the catalogue does not: {unknown}")
    held_out = [p for p in files if meta[p]["split"] != "development"]
    if held_out:
        die(f"the panel holds parts that are not development material: {held_out}")
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(args.workers) as ex:
        lags = dict(ex.map(measure, [(p, files[p], meta[p]["lag"], crops)
                                     for p in sorted(files)]))
    for part, row in lags.items():
        record = json.loads((crops / part / "record.json").read_text())
        row["crop"] = {"excerpt_start_frame": record["excerpt_start_frame"],
                       "excerpt_end_frame": record["excerpt_end_frame"]}
    document = {
        "schema": "validation-lags-3",
        "meaning": "lag_samples: samples the part's amp track lags its DI at 48 kHz "
                   "(recording[t] ~ di[t - lag_samples]), measured on the part's 10-s "
                   "validation crop",
        "method": "scripts/record_part_lags.py: candidates from the pooled correlation "
                  "with the panel's renders, chosen by the judge when several and then "
                  "confirmed by a clear onset peak, checked against the DI's onsets",
        "panel": str(args.panel_dir), "latency_samples": LATENCY,
        "catalogue_sha256": _sha(CATALOG), "panel_index_sha256": _sha(panel / "index.json"),
        "parts": lags}
    args.json.expanduser().write_text(json.dumps(document, indent=1) + "\n")
    print(f"{len(lags)} parts; ambiguous: {[p for p, r in lags.items() if r['ambiguous']]}; "
          f"onset disagrees: {[p for p, r in lags.items() if r['onset_disagrees']]}")


if __name__ == "__main__":
    guarded(main)
