#!/usr/bin/env python3
"""Which distance without a DI reproduces the judge's choices? (`docs/di-free-distance-plan.md`)

    python research/di_free_distance.py --json docs/di-free-distance.json

For each of the 25 amp-reach parts, every menu candidate as rendered through each
donor part's DI (an active part of another band, so other notes) is compared with the
part's amp track, and with its separated guitar on the parts with a qualified stem, by
each DI-free distance ("row"). A row's pick is the nearest; its regret is how much
farther that pick is under the judge (through the part's own DI) than the judge's best.
Every clip's features are computed once and cached under `--cache`
(`--features-only` stops there).
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
import pathlib
import pickle
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.append(str(PLUGIN_ROOT / "scripts"))

from _cli import die, guarded

KILL = pathlib.Path("~/ndsp-presets/runs/kill")
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops")
STEMS = pathlib.Path("~/ndsp-presets/learn/poc/stems")
STEM_MODEL = "htdemucs_6s"
STEM_SNR_DB = 1.0
AVG = pathlib.Path("~/ndsp-presets/learn/di-robust/avg-yardstick-distances.json")
AMPS = ("sw50r", "pr12", "ac20")
BAND_SETS = ("recording", "union")
MENUS = ("all", "clean")
RATE = 48000
WINDOW_S = (1.0, 10.0)
HALF_B_S = (5.5, 10.0)
LOUDNESS = -23.0
GATE_DB = 40.0                  # frames within this of the clip's loudest are kept
FRAME_FLOOR_DB = 40.0           # masked rows: each band floored this far under the frame's peak
MASK_DB = 30.0                  # masked rows: bands within this of the reference's peak
MELS, FMIN, FMAX = 64, 50.0, 16000.0
N_FFT, HOP = 4096, 1024
MFCCS = 20
LDA_DIMS = 40
GATE_RATIO = 0.75
GATE_SPEARMAN = 0.6
GATE_P = 0.05
NEAR_TIE = 0.09
ROWS = ("v3", "v3c", "long_term_spectrum", "log_mel_mean_spread", "mfcc_statistics",
        "lean_fingerprint", "masked_long_term_spectrum", "masked_log_mel_mean_spread", "lda")
TESTED = ROWS[1:]


# --- clips and features -------------------------------------------------------------

def clip(path, window=WINDOW_S):
    """Mono, cut to a window, at one loudness."""
    import numpy as np

    from analysis import io

    audio = io.load(path)
    if audio.sample_rate != RATE:
        raise ValueError(f"{path} is not at {RATE} Hz")
    x = audio.mono()[round(window[0] * RATE):round(window[1] * RATE)]
    lufs = io.loudness_lufs(io.from_samples(x, RATE))
    if lufs is None or not math.isfinite(lufs):
        raise ValueError(f"{path} is too quiet to measure")
    return (x * 10 ** ((LOUDNESS - lufs) / 20)).astype(np.float64)


def mel_filters():
    import numpy as np

    mel = lambda f: 2595 * np.log10(1 + f / 700)            # noqa: E731
    hz = lambda m: 700 * (10 ** (m / 2595) - 1)              # noqa: E731
    edges = hz(np.linspace(mel(FMIN), mel(FMAX), MELS + 2))
    freqs = np.fft.rfftfreq(N_FFT, 1 / RATE)
    bank = np.zeros((MELS, len(freqs)))
    for i in range(MELS):
        lo, mid, hi = edges[i:i + 3]
        bank[i] = np.clip(np.minimum((freqs - lo) / (mid - lo), (hi - freqs) / (hi - mid)),
                          0, None)
    return bank


def gated_log_mel(x):
    """[frames, MELS] log-mel in dB over the frames within GATE_DB of the loudest: gated
    by the clip's own level, never by a DI."""
    import numpy as np

    window = np.hanning(N_FFT)
    starts = range(0, len(x) - N_FFT, HOP)
    power = np.array([np.abs(np.fft.rfft(x[i:i + N_FFT] * window)) ** 2 for i in starts])
    level = 10 * np.log10(power.sum(axis=1) + 1e-20)
    keep = level >= level.max() - GATE_DB
    return 10 * np.log10(power[keep] @ mel_filters().T + 1e-12)


def mel_stats(x) -> dict:
    """The log-mel statistics, plain and with each frame floored FRAME_FLOOR_DB under its
    loudest band (as the judge floors its frames)."""
    import numpy as np

    mel = gated_log_mel(x)
    floored = np.maximum(mel, mel.max(axis=1, keepdims=True) - FRAME_FLOOR_DB)
    return {"mel_mean": mel.mean(axis=0), "mel_std": mel.std(axis=0),
            "floor_mean": floored.mean(axis=0), "floor_std": floored.std(axis=0),
            "mel": mel}


def features(job) -> tuple:
    """(key, feature dict) for one clip: the log-mel and MFCC statistics, the lean
    fingerprint vector, and the full fingerprint for the v3 rows."""
    import numpy as np
    from scipy.fft import dct

    from analysis import io
    from analysis.fingerprint import fingerprint

    key, path, regime, window = job
    try:
        x = clip(path, window)
    except ValueError:
        return key, None                    # silent in this window: recorded, then skipped
    stats = mel_stats(x)
    mfcc = dct(stats.pop("mel"), type=2, norm="ortho", axis=1)[:, 1:MFCCS + 1]
    fp = fingerprint(io.from_samples(x, RATE), regime=regime, excerpt_s=None)
    s, d = fp.spectrum, fp.dynamics
    bands = np.array(s["band_db"], dtype=float)
    lean = np.concatenate([
        bands - bands.mean(),
        [s["tilt_db_per_decade"]],
        [math.log10(s["centroid_hz"][p]) for p in ("p10", "p50", "p90")],
        [math.log10(s["rolloff85_hz"]["p50"])],
        [math.log10(max(s["flatness"]["p50"], 1e-12))],
        [d["crest_db"], d["lra_lu"]]])
    return key, {**stats, "mfcc": np.concatenate([mfcc.mean(axis=0), mfcc.std(axis=0)]),
                 "lean": lean, "fp": fp.to_dict()}


def floor_stats(job) -> tuple:
    """(key, the floored log-mel statistics) for a clip cached before they existed."""
    key, path, _, window = job
    stats = mel_stats(clip(path, window))
    return key, {"floor_mean": stats["floor_mean"], "floor_std": stats["floor_std"]}


# --- distances ----------------------------------------------------------------------

def euclid(a, b, scale=None) -> float:
    """Euclidean, over the values both sides have (a loudness range can be empty)."""
    import numpy as np

    diff = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if scale is not None:
        diff = diff / scale
    diff = diff[np.isfinite(diff)]
    return float(np.linalg.norm(diff)) if len(diff) else float("nan")


def masked(ref_mean, ref_spread, cand_mean, cand_spread=None) -> float:
    """The judge's treatment, from the reference alone: only the bands within MASK_DB of
    the reference's peak, and the mean level offset between the two removed."""
    import numpy as np

    keep = np.asarray(ref_mean) >= np.max(ref_mean) - MASK_DB
    diff = np.asarray(ref_mean)[keep] - np.asarray(cand_mean)[keep]
    diff = diff - diff.mean()
    if cand_spread is not None:
        diff = np.concatenate([diff, np.asarray(ref_spread)[keep] - np.asarray(cand_spread)[keep]])
    return float(np.linalg.norm(diff))


def make_rows(scales):
    """{row: distance(reference features, render features)}; the LDA row is built apart,
    since it depends on the target's band."""
    import numpy as np

    from analysis.compare import Objectives, compare, scalar
    from kill_tests import _v3c_compare

    v3c_compare = _v3c_compare()

    def v3(ref, ren):
        o = compare(ref["fpo"], ren["fpo"], profile="unpaired-v3")
        return scalar(Objectives(values={k: v for k, v in o.values.items() if k != "level"},
                                 profile="unpaired-v3"))

    return {
        "v3": v3,
        "v3c": lambda r, c: v3c_compare(r["fpo"], c["fpo"]),
        "long_term_spectrum": lambda r, c: euclid(r["mel_mean"], c["mel_mean"]),
        "log_mel_mean_spread": lambda r, c: euclid(
            np.concatenate([r["mel_mean"], r["mel_std"]]),
            np.concatenate([c["mel_mean"], c["mel_std"]])),
        "mfcc_statistics": lambda r, c: euclid(r["mfcc"], c["mfcc"], scales["mfcc"]),
        "lean_fingerprint": lambda r, c: euclid(lean_of(r), lean_of(c), scales["lean"]),
        "masked_long_term_spectrum": lambda r, c: masked(r["floor_mean"], None,
                                                         c["floor_mean"]),
        "masked_log_mel_mean_spread": lambda r, c: masked(r["floor_mean"], r["floor_std"],
                                                          c["floor_mean"], c["floor_std"]),
    }


def lean_of(feats):
    """The lean vector as floats, an empty field (a loudness range too short to measure)
    as NaN."""
    import numpy as np

    return np.array([np.nan if v is None else v for v in feats["lean"]], dtype=float)


def lda_vector(feats, scales):
    """MFCC statistics and the lean fingerprint, scaled; an empty field takes its median
    over the panel renders, so the projection has every value."""
    import numpy as np

    lean = np.where(np.isfinite(lean_of(feats)), lean_of(feats), scales["lean_median"])
    return np.concatenate([feats["mfcc"] / scales["mfcc"], lean / scales["lean"]])


def fit_lda(X, y, dims: int = LDA_DIMS):
    """The leading `dims` linear discriminants of X for the labels y."""
    import numpy as np
    from scipy.linalg import eigh

    X = np.asarray(X, dtype=float)
    mean = X.mean(axis=0)
    within = np.zeros((X.shape[1], X.shape[1]))
    between = np.zeros_like(within)
    labels = list(y)
    for label in sorted(set(labels)):
        rows = X[[i for i, v in enumerate(labels) if v == label]]
        centred = rows - rows.mean(axis=0)
        within += centred.T @ centred
        gap = (rows.mean(axis=0) - mean)[:, None]
        between += len(rows) * gap @ gap.T
    within += np.eye(len(within)) * 1e-3 * np.trace(within) / len(within)
    values, vectors = eigh(between, within)
    return vectors[:, np.argsort(values)[::-1][:dims]]


# --- statistics ---------------------------------------------------------------------

def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2
        i = j + 1
    return out


def spearman(a, b) -> float:
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else 0.0


def band_medians(values: dict, bands: dict) -> dict:
    by = collections.defaultdict(list)
    for part, value in values.items():
        if value is not None:
            by[bands[part]].append(value)
    return {b: statistics.median(v) for b, v in by.items()}


def band_stat(values: dict, bands: dict):
    """The median across bands of each band's median: every band counts once."""
    medians = band_medians(values, bands)
    return statistics.median(medians.values()) if medians else None


def sign_flip_p(diffs) -> float:
    """One-sided exact p that the sum of the differences is this low (or lower) when each
    one's sign is flipped at random."""
    observed = sum(diffs)
    flips = list(itertools.product((1, -1), repeat=len(diffs)))
    return sum(sum(s * d for s, d in zip(signs, diffs)) <= observed + 1e-12
               for signs in flips) / len(flips)


def holm(ps: dict) -> dict:
    """Holm-adjusted p-values."""
    order = sorted(ps, key=ps.get)
    out, running = {}, 0.0
    for i, name in enumerate(order):
        running = max(running, min(1.0, (len(order) - i) * ps[name]))
        out[name] = running
    return out


def finite(v) -> bool:
    return v is not None and math.isfinite(v)


def regret_of(judged: dict, pick: str) -> float:
    return math.log(judged[pick]) - math.log(min(judged.values()))


# --- inputs -------------------------------------------------------------------------

def load_inputs():
    """Panels, judge distances, bands, quiet parts, stems."""
    from benchmark_recordings import CATALOG

    kill = KILL.expanduser()
    files = collections.defaultdict(dict)          # files[part][candidate] = path
    for amp in AMPS:
        index = json.loads((kill / amp / "index.json").read_text())
        for row in index["rows"]:
            if "file" in row and "part" in row:
                files[row["part"]][f"{amp}:{row['candidate']}"] = pathlib.Path(row["file"])
    reach = json.loads((kill / "amp-reach.json").read_text())
    catalog = json.loads(pathlib.Path(CATALOG).read_text(encoding="utf-8"))
    bands = {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            bands[slug] = s.get("group") or f"{s['source']}/{s['song']}"
    manifest = json.loads((STEMS.expanduser() / "manifest.json").read_text())["parts"]
    stems = {p: pathlib.Path(m["files"][STEM_MODEL]["mix_guitar"])
             for p, m in manifest.items()
             if m.get("usable") and m["stems"][STEM_MODEL]["mix"]["snr_db"] >= STEM_SNR_DB}
    return files, reach, bands, set(reach["parts_with_a_quiet_half"]), stems


def judge(reach, part: str, band_set: str, window: str = "full") -> dict:
    """{candidate: judge distance} for one window and band set."""
    out = {}
    for key, value in reach["distances"][part].items():
        name, w, b = key.rsplit("|", 2)
        if w == window and b == band_set and value is not None and value > 0:
            out[name] = value
    return out


def clean_menu(menu) -> list:
    """Each amp's template+R and its factory presets `high_gain` calls clean."""
    from plan_listening_validation import high_gain

    return [c for c in menu if c.endswith("template+R") or not high_gain(c)]


# --- the check ----------------------------------------------------------------------

def cache_features(args, jobs) -> dict:
    from concurrent.futures import ProcessPoolExecutor

    path = args.cache.expanduser()
    cache = pickle.loads(path.read_bytes()) if path.exists() else {}
    path.parent.mkdir(parents=True, exist_ok=True)
    stages = (("features", features, [j for j in jobs if j[0] not in cache]),
              ("floored statistics", floor_stats,
               [j for j in jobs if cache.get(j[0]) is not None
                and "floor_mean" not in cache[j[0]]]))
    for kind, work, todo in stages:
        if not todo:
            continue
        with ProcessPoolExecutor(args.workers) as ex:
            for n, (key, feats) in enumerate(ex.map(work, todo, chunksize=8), 1):
                if feats is None:
                    cache[key] = None
                else:
                    cache.setdefault(key, {}).update(feats)
                if n % 500 == 0:
                    path.write_bytes(pickle.dumps(cache))
                    print(f"{kind}: {n} of {len(todo)} clips", flush=True)
        path.write_bytes(pickle.dumps(cache))
    return cache


def distance_tables(rows, lda, cache, targets, donors, menu, bands, prefix=()):
    """{row: {(kind, part): {donor, or the part itself: {candidate: distance}}}}:
    distances do not depend on the band set or menu, so each is computed once."""
    out = {}
    for name in list(rows) + ["lda"]:
        table = {}
        for p in targets:
            for kind in ("reference", "stem"):
                ref_key = prefix + (kind, p)
                if ref_key not in cache:
                    continue
                if name == "lda":
                    project = lda[bands[p]]
                    ref_vec = project(cache[ref_key])

                    def distance(key, ref_vec=ref_vec, project=project):
                        return euclid(ref_vec, project(cache[key]))
                else:
                    def distance(key, ref=cache[ref_key], f=rows[name]):
                        return f(ref, cache[key])
                sources = donors[p] + ([p] if kind == "reference" else [])
                table[(kind, p)] = {q: {c: distance(prefix + (q, c)) for c in menu
                                        if prefix + (q, c) in cache} for q in sources}
        out[name] = table
        print(f"distances: {name}{' (half B)' if prefix else ''}", flush=True)
    return out


def score_row(table, judged, clean, targets, bands, kind: str, menu: list) -> dict:
    """A row's regret, agreement and readings on one menu, against one kind of reference.
    A part's figure over its donors is the median over donor bands of each band's
    median, so every donor band counts once."""
    regrets, agreements, own_share = {}, {}, {}
    per_amp = collections.defaultdict(dict)
    for p in targets:
        if (kind, p) not in table:
            continue
        by_donor = table[(kind, p)]
        donors = [q for q in by_donor if q != p]
        regret_q, rho_q, own_q = {}, {}, {}
        amp_q = collections.defaultdict(dict)
        for q in donors:
            dist = {c: v for c, v in by_donor[q].items() if c in menu and finite(v)}
            if not dist:
                continue
            pick = min(dist, key=dist.get)
            # The judge's best is over the whole menu: an empty distance only drops a
            # candidate from the pick.
            regret_q[q] = regret_of({c: judged[p][c] for c in menu}, pick)
            on_clean = [c for c in clean if finite(by_donor[q].get(c))]
            rho_q[q] = spearman([by_donor[q][c] for c in on_clean],
                                [judged[p][c] for c in on_clean])
            for amp in AMPS:
                sub = {c: v for c, v in dist.items() if c.startswith(amp + ":")}
                if sub:
                    amp_q[amp][q] = regret_of({c: judged[p][c] for c in menu
                                               if c.startswith(amp + ":")},
                                              min(sub, key=sub.get))
            if p in by_donor:
                mixed = {("donor", c): v for c, v in dist.items()}
                mixed.update({("own", c): by_donor[p][c] for c in dist
                              if finite(by_donor[p].get(c))})
                own_q[q] = float(min(mixed, key=mixed.get)[0] == "own")
        regrets[p] = band_stat(regret_q, bands)
        agreements[p] = band_stat(rho_q, bands)
        if own_q:
            own_share[p] = band_stat(own_q, bands)
        for amp, values in amp_q.items():
            per_amp[amp][p] = band_stat(values, bands)
    return {
        "regret": band_stat(regrets, bands), "agreement": band_stat(agreements, bands),
        "parts": len(regrets), "per_part_regret": regrets, "per_part_agreement": agreements,
        "per_band_regret": band_medians(regrets, bands),
        "per_amp_regret": {a: band_stat(v, bands) for a, v in per_amp.items()},
        "own_di_share": band_stat(own_share, bands) if own_share else None,
    }


def constant_regrets(judged, targets, bands, menu) -> dict:
    """The song-blind constant: for each part, the candidate with the lowest median judge
    distance over the parts of the other bands."""
    out = {}
    for p in targets:
        others = [q for q in targets if bands[q] != bands[p]]
        pick = min(menu, key=lambda c: statistics.median(judged[q][c] for q in others))
        out[p] = regret_of({c: judged[p][c] for c in menu}, pick)
    return out


def gate(result, bands) -> dict:
    """The declared stop and gate."""
    blocks = result["by_band_set"]
    out = {"stop_v3_is_enough": all(blocks[b][m]["v3"]["reference"]["regret"] <= NEAR_TIE
                                    for b in BAND_SETS for m in MENUS)}
    tests = {}
    for b in BAND_SETS:
        for m in MENUS:
            const_bands = band_medians(blocks[b][m]["constant"]["per_part_regret"], bands)
            ps = {}
            for name in TESTED:
                row_bands = blocks[b][m][name]["reference"]["per_band_regret"]
                ps[name] = sign_flip_p([row_bands[x] - const_bands[x] for x in sorted(row_bands)])
            tests[(b, m)] = holm(ps)
    for name in TESTED:
        verdicts = {}
        for b in BAND_SETS:
            for m in MENUS:
                block = blocks[b][m]
                row, base, constant = block[name], block["v3"], block["constant"]
                stem_parts = set(row["stem"]["per_part_regret"])
                const_stems = band_stat({p: v for p, v in constant["per_part_regret"].items()
                                         if p in stem_parts}, bands)
                verdicts[f"{b}/{m}"] = {
                    "regret": row["reference"]["regret"] <= GATE_RATIO * min(
                        constant["regret"], base["reference"]["regret"]),
                    "beats_constant_p": tests[(b, m)][name],
                    "beats_constant": tests[(b, m)][name] < GATE_P,
                    "agreement": row["reference"]["agreement"] >= GATE_SPEARMAN,
                    "stems": row["stem"]["regret"] is not None
                    and row["stem"]["regret"] <= const_stems,
                }
        out[name] = {"verdicts": verdicts, "passes": all(
            v["regret"] and v["beats_constant"] and v["agreement"] and v["stems"]
            for v in verdicts.values())}
    passing = [n for n in TESTED if out[n]["passes"]]
    if out["stop_v3_is_enough"]:
        out["answer"] = "v3"                # the gate results are then for information
    else:
        out["answer"] = (min(passing, key=lambda n: max(
            blocks[b][m][n]["stem"]["regret"] for b in BAND_SETS for m in MENUS))
            if passing else None)
    return out


def another_teacher(rows, lda, cache, targets, donors, avg_menu, bands, reach, avg):
    """Each row's regret on the clean PR12 menu, every clip cut to half B, under the
    average-guitar measure and under the judge's half-B distance: reported, not
    deciding."""
    if not avg_menu:
        return None
    dists = distance_tables(rows, lda, cache, targets, donors, avg_menu, bands, prefix=("B",))
    out = {}
    for band_set in BAND_SETS:
        teachers = {
            "average_guitar": {p: {f"pr12:{c}": v for c, v in
                                   ((avg.get(p) or {}).get(f"{band_set}|B") or {}).items() if v}
                               for p in targets},
            "judge_half_b": {p: judge(reach, p, band_set, "B") for p in targets}}
        out[band_set] = {}
        for teacher, scores in teachers.items():
            out[band_set][teacher] = {}
            for name, table in dists.items():
                regrets = {}
                for p in targets:
                    have = [c for c in avg_menu if c in scores[p]]
                    if not have or ("reference", p) not in table:
                        continue
                    per = {}
                    for q, dist in table[("reference", p)].items():
                        if q == p:
                            continue
                        sub = {c: dist[c] for c in have if finite(dist.get(c))}
                        if not sub:
                            continue
                        per[q] = regret_of({c: scores[p][c] for c in have}, min(sub, key=sub.get))
                    regrets[p] = band_stat(per, bands)
                out[band_set][teacher][name] = band_stat(regrets, bands)
    return out


def run(args):
    import numpy as np

    from analysis.fingerprint import Fingerprint

    files, reach, bands, quiet, stems = load_inputs()
    targets = list(reach["parts"])
    if any(p not in bands for p in targets):
        die(f"no band for {[p for p in targets if p not in bands]}")
    menu = sorted(c for c in set.intersection(*(set(files[p]) for p in files))
                  if all(c in judge(reach, p, "recording") for p in targets))
    donors = {p: [q for q in files if q not in quiet and bands.get(q) not in (None, bands[p])]
              for p in targets}
    avg = json.loads(AVG.expanduser().read_text()) if AVG.expanduser().exists() else {}
    avg_menu = sorted({f"pr12:{c}" for p in avg for c in (avg[p].get("recording|B") or {})}
                      & set(menu))
    used = {q for p in targets for q in donors[p]} | set(targets)
    jobs = [((q, c), files[q][c], "probe", WINDOW_S) for q in files for c in menu]
    jobs += [(("reference", p), CROPS.expanduser() / p / "reference.wav", "isolated_stem",
              WINDOW_S) for p in targets]
    jobs += [(("stem", p), stems[p], "isolated_stem", WINDOW_S) for p in targets if p in stems]
    jobs += [(("B", q, c), files[q][c], "probe", HALF_B_S) for q in sorted(used)
             for c in avg_menu]
    jobs += [(("B", "reference", p), CROPS.expanduser() / p / "reference.wav",
              "isolated_stem", HALF_B_S) for p in targets]
    cache = cache_features(args, jobs)
    if args.features_only:
        print(f"{len(cache)} clips' features cached at {args.cache.expanduser()}")
        return
    # Only the qualified stems are used, whatever an earlier run cached.
    silent = sorted(str(k) for k, v in cache.items() if v is None)
    cache = {k: v for k, v in cache.items()
             if v is not None and not (k[0] == "stem" and k[1] not in stems)}
    for feats in cache.values():
        feats["fpo"] = Fingerprint.from_dict(feats["fp"])
    renders = [cache[(q, c)] for q in files for c in menu if (q, c) in cache]
    lean_all = np.array([lean_of(f) for f in renders])
    scales = {"mfcc": np.std(np.array([f["mfcc"] for f in renders]), axis=0) + 1e-9,
              "lean": np.nanstd(lean_all, axis=0) + 1e-9,
              "lean_median": np.nanmedian(lean_all, axis=0)}
    rows = make_rows(scales)
    lda = {}
    for band in sorted({bands[p] for p in targets}):
        train = [(q, c) for q in files if q not in quiet and bands.get(q) not in (None, band)
                 for c in menu if (q, c) in cache]
        W = fit_lda([lda_vector(cache[k], scales) for k in train], [c for _, c in train])
        lda[band] = lambda feats, W=W: lda_vector(feats, scales) @ W
    clean = clean_menu(menu)
    menus = {"all": menu, "clean": clean}
    dists = distance_tables(rows, lda, cache, targets, donors, menu, bands)
    empty = {n: sum(not finite(v) for t in dists[n].values() for d in t.values() for v in d.values())
             for n in dists}
    result = {"schema": "di-free-distance-2", "parts": targets,
              "menu_sizes": {m: len(v) for m, v in menus.items()},
              "donors_per_part": {p: len(donors[p]) for p in targets},
              "stem_parts": sorted(p for p in targets if p in stems),
              "empty_distances": empty, "silent_clips": silent, "by_band_set": {}}
    for band_set in BAND_SETS:
        judged = {p: judge(reach, p, band_set) for p in targets}
        result["by_band_set"][band_set] = {}
        for m, items in menus.items():
            block = result["by_band_set"][band_set][m] = {}
            random = {p: statistics.mean(regret_of({c: judged[p][c] for c in items}, c)
                                         for c in items) for p in targets}
            constant = constant_regrets(judged, targets, bands, items)
            block["random"] = {"regret": band_stat(random, bands)}
            block["constant"] = {"regret": band_stat(constant, bands),
                                 "per_part_regret": constant}
            for name in ROWS:
                block[name] = {kind: score_row(dists[name], judged, clean, targets, bands,
                                               kind, items)
                               for kind in ("reference", "stem")}
                print(f"{band_set} {m} {name}: regret "
                      f"{block[name]['reference']['regret']:.3f}", flush=True)
    result["gate"] = gate(result, bands)
    result["another_teacher"] = another_teacher(rows, lda, cache, targets, donors, avg_menu,
                                                bands, reach, avg)
    args.json.write_text(json.dumps(result, indent=1, default=float) + "\n")
    print(json.dumps(result["gate"], indent=1, default=float))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--cache", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/runs/di-free/features.pkl"))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--features-only", action="store_true",
                    help="compute and cache every clip's features, and stop")
    args = ap.parse_args()
    if not args.features_only and not args.json:
        die("--json is required unless --features-only")
    run(args)


if __name__ == "__main__":
    guarded(main)
