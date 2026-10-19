"""Released mix previews vs our unity sums (`docs/mix-previews-results.md`). Zero renders.

    .venv/bin/python -m learn.mix_previews align          # alignment.json (CPU, light)
    nice -n 19 $MSST_PY -m learn.mix_previews separate    # Mega-53 on the aligned preview contexts
    .venv/bin/python -m learn.mix_previews report

MSST_PY is ~/ndsp-presets/tools/msst-venv/bin/python. Inputs: ~/ndsp-presets/references/mix-previews/
(Cambridge "Full Preview" MP3s, mastered; 1003_Remix.mp3 is Sound On Sound's Mix Rescue remix of
Signs; `*_UnmasteredWAV.wav` where present). Outputs: alignment.json there, the rest under
~/ndsp-presets/learn/mix-previews/.

Alignment. Our session is the unity sum of the stage F / label-table record's `included_mix_tracks`
(mono channel mean, 48 kHz via `analysis.io.load`, first-sample aligned, as the crops). The preview
is folded to mono and resampled 44.1 -> 48 kHz the same way. A whole-file GCC-PHAT gives the three
strongest global offsets. Every 4-s preview block (hop 2 s) gets candidate positions from its own
10-ms log-energy envelope search over the whole session (normalised cross-correlation) and from
the three global offsets; each is refined to the sample by GCC-PHAT within ±20 ms (edge hits
dropped) and the candidate with the higher Pearson r of the aligned waveforms wins, except that the
strongest global offset keeps the block when its r is within 0.02 of the best (songs repeat
copy-pasted sections, which otherwise split spans on noise). Blocks match
when at least 3 of them agree on the offset (chained within 2 ms); runs of matched blocks in one
offset cluster, bridging unmatched blocks, form a span (`offset = session frame − preview frame`,
both at 48 kHz) with a fitted linear drift. A second cluster means an edit or repeated audio;
no cluster means a different take or arrangement.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
IN = HOME / "references/mix-previews"
OUT = HOME / "learn/mix-previews"
SR = 48000
CROP = 480_000
HOP = 480                       # 10-ms envelope frames
BLOCK_S, STEP_S = 4.0, 2.0
REFINE = 960                    # ±20 ms GCC search around the envelope lag
CLUSTER_GAP = 96                # samples (2 ms): blocks whose offsets chain within this agree
SUPPORT = 3                     # blocks that must agree before an offset counts
GLOBAL_PEAKS = 3                # whole-file GCC-PHAT candidates tried in every block
TIE_R = 0.02                    # a block keeps the main (strongest global) offset unless another wins by more
QUIET_DB = -45.0                # blocks quieter than this (preview dBFS RMS) are not judged
SONGS = {                       # preview stem -> (song in the records, label-table slug prefix)
    "GetOutOfBed": "Get Out Of Bed", "TodaysTheDay": "Today's The Day", "Magilla": "Magilla",
    "ItWasMyFaultForWaiting": "It Was My Fault For Waiting", "ColourMeRed": "Colour Me Red",
    "LetsDance": "Let's Dance", "PassingShips": "Passing Ships", "Quicksand": "Quicksand",
    "Wickerman": "Wickerman", "Femme": "Femme", "Signs": "Signs",
}


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def preview_files():
    """{song: [(kind, path)]}: the mastered preview and, where present, the unmastered WAV."""
    out = {}
    for stem, song in SONGS.items():
        files = []
        mp3 = IN / ("1003_Remix.mp3" if stem == "Signs" else f"{stem}_Full_Preview.mp3")
        if mp3.exists():
            files.append(("remix_mastered" if stem == "Signs" else "preview_mastered", mp3))
        for w in sorted(IN.glob(f"*{stem}*_UnmasteredWAV.wav")):
            files.append(("unmastered", w))
        out[song] = files
    return out


# --- pure parts (tested) ----------------------------------------------------------------------------

def envelope(x, hop=HOP):
    """Mean-removed log energy per `hop` frame."""
    import numpy as np

    n = len(x) // hop
    e = np.log10(np.mean(np.asarray(x[:n * hop], np.float64).reshape(n, hop) ** 2, 1) + 1e-10)
    return e - e.mean()


def ncc_lag(q, ref):
    """(lag, r): where envelope q best fits inside ref (ref[lag:lag+len(q)] ~ q), by normalised
    cross-correlation over every full-overlap lag."""
    import numpy as np
    from scipy.signal import fftconvolve

    m = len(q)
    if m > len(ref):
        return None, -1.0
    q = q - q.mean()
    qn = np.sqrt(np.sum(q ** 2)) + 1e-12
    num = fftconvolve(ref, q[::-1], mode="valid")
    c1 = np.concatenate([[0.0], np.cumsum(ref)])
    c2 = np.concatenate([[0.0], np.cumsum(ref ** 2)])
    s1, s2 = c1[m:] - c1[:-m], c2[m:] - c2[:-m]
    var = np.maximum(s2 - s1 ** 2 / m, 1e-12)
    r = num / (qn * np.sqrt(var))
    k = int(np.argmax(r))
    return k, float(r[k])


def gcc_phat(a, b, max_lag):
    """The integer lag d (|d| <= max_lag) with a[t] ~ b[t + d]."""
    import numpy as np

    n = len(a) + len(b)
    nfft = 1 << int(np.ceil(np.log2(n)))
    A, B = np.fft.rfft(a, nfft), np.fft.rfft(b, nfft)
    R = B * np.conj(A)
    cc = np.fft.irfft(R / (np.abs(R) + 1e-12), nfft)
    cc = np.concatenate([cc[-max_lag:], cc[:max_lag + 1]])
    return int(np.argmax(cc)) - max_lag


def clusters(blocks, gap=CLUSTER_GAP, support=SUPPORT):
    """Mark blocks whose sample offsets agree with at least `support` − 1 others (offsets sorted
    and split where neighbours differ by more than `gap`): sets `cluster` (an id, or None) and
    `matched` on every block. Unrelated audio lands at scattered offsets across the session, so
    agreement, not waveform correlation, is the evidence."""
    idx = sorted((b["offset"], i) for i, b in enumerate(blocks) if b.get("offset") is not None)
    groups, cur = [], []
    for o, i in idx:
        if cur and o - cur[-1][0] > gap:
            groups.append(cur)
            cur = []
        cur.append((o, i))
    if cur:
        groups.append(cur)
    for b in blocks:
        b["cluster"], b["matched"] = None, False
    for g in groups:
        if len(g) >= support:
            cid = int(sorted(o for o, _ in g)[len(g) // 2])
            for _, i in g:
                blocks[i]["cluster"], blocks[i]["matched"] = cid, True
    return blocks


def spans(blocks, only=None):
    """Runs of matched blocks (preview order) in one cluster; unmatched blocks between two blocks
    of the same cluster are bridged (no evidence is not counter-evidence), a block of another
    cluster ends the run (an edit). With `only`, other clusters count as unmatched (the main
    offset's spans). Each span's offset is a line over preview time (drift)."""
    import numpy as np

    runs, cur = [], None
    judged = [b for b in blocks if b["judged"]]
    for b in blocks:
        if not b["matched"] or (only is not None and b["cluster"] != only):
            continue
        if cur and b["cluster"] == cur[0]["cluster"]:
            cur.append(b)
        else:
            if cur:
                runs.append(cur)
            cur = [b]
    if cur:
        runs.append(cur)
    res = []
    for run in runs:
        p0, p1 = run[0]["p0"], run[-1]["p1"]
        t = np.array([(b["p0"] + b["p1"]) / 2 for b in run], float)
        o = np.array([b["offset"] for b in run], float)
        slope, icpt = (np.polyfit(t, o, 1) if len(run) >= 3 and np.ptp(t) > 0 else (0.0, float(np.median(o))))
        inside = [b for b in judged if p0 <= b["p0"] and b["p1"] <= p1]
        rs = [b["r"] for b in run]
        res.append({"preview_start_s": round(p0 / SR, 2), "preview_end_s": round(p1 / SR, 2),
                    "session_start_s": round((p0 + icpt + slope * p0) / SR, 2),
                    "session_end_s": round((p1 + icpt + slope * p1) / SR, 2),
                    "offset_samples": int(round(icpt + slope * p0)), "drift_ppm": round(float(slope) * 1e6, 2),
                    "intercept": float(icpt), "slope": float(slope),
                    "max_residual_samples": int(np.max(np.abs(o - (icpt + slope * t)))),
                    "n_blocks": len(run), "judged_blocks": len(inside),
                    "evidence_share": round(len(run) / max(1, len(inside)), 3),
                    "median_r": round(float(np.median(rs)), 3), "min_r": round(float(np.min(rs)), 3)})
    return res


def offset_at(span, p):
    """The span's offset (session − preview frame) at preview frame p."""
    return int(round(span["intercept"] + span["slope"] * p))


def covered(a, b, sp):
    """Share of session frames [a, b) inside a span (session time), and the span holding the
    whole window (None unless one span does)."""
    whole, inside = None, 0
    for s in sp:
        s0, s1 = round(s["session_start_s"] * SR), round(s["session_end_s"] * SR)
        inside += max(0, min(b, s1) - max(a, s0))
        if s0 <= a and b <= s1:
            whole = s
    return min(1.0, inside / (b - a)), whole


def same_take(main_sp, judged_s, preview_s, main_r=None, alt_r=None, alt_share=0.0):
    """yes: the main offset's span covers ≥ 80% of the judged (non-quiet) preview and no other
    offset fits better (other clusters' median r below the main one's, under 25% of matched
    blocks); partial: less coverage, or another offset that fits as well (an edit); no: nothing."""
    if not main_sp:
        return "no"
    span_s = sum(s["preview_end_s"] - s["preview_start_s"] for s in main_sp)
    rival = alt_r is not None and (alt_r >= main_r or alt_share >= 0.25)
    if span_s >= 0.8 * min(judged_s, preview_s) and not rival:
        return "yes"
    return "partial"


def crop_check(mix, y, a, b, off, search=3 * SR):
    """The crop's own GCC-PHAT: the preview's samples for session [a, b) at offset `off`, searched
    in the session within ±`search`. -> (deviation from off in samples, peak height in SDs of the
    correlation, Pearson r at off); None when the preview lacks the crop."""
    import numpy as np

    p0, p1 = a - off, b - off
    if p0 < 0 or p1 > len(y):
        return None
    seg = y[p0:p1]
    lo, hi = max(0, a - search), min(len(mix), b + search)
    ref = mix[lo:hi]
    nfft = 1 << int(np.ceil(np.log2(len(seg) + len(ref))))
    R = np.fft.rfft(ref, nfft) * np.conj(np.fft.rfft(seg, nfft))
    cc = np.fft.irfft(R / (np.abs(R) + 1e-12), nfft)[:len(ref) - len(seg) + 1]
    k = int(np.argmax(cc))
    return {"deviation_samples": int(lo + k - a), "peak_sd": round(float(cc[k] / (np.std(cc) + 1e-20)), 1),
            "r_at_offset": round(float(np.corrcoef(seg, mix[a:b])[0, 1]), 3)}


CROP_OK_SD = 8.0                # the crop's own GCC peak must stand this far above its spread
CROP_OK_DEV = 96                # ... within 2 ms of the main offset


# --- align -------------------------------------------------------------------------------------------

def song_records(song):
    """{slug: (part, record, crop window)} for every label-table part of the song (stage F is a
    subset), and the session folder."""
    from learn import arm_a_mega53 as A
    from learn import separate as SEP

    lt = A.lt_parts()
    cat12 = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    pool = set(A.pool_slugs())
    out, folder = {}, None
    for slug, p in lt.items():
        crop = pathlib.Path(p["crop"])
        rec = json.loads((crop / "record.json").read_text())
        if not slug.startswith("cambridge-") or rec["song"] != song:
            continue
        cat = cat12 if p["set"] == 12 else A.shim_catalog(rec)
        s = [x for x in cat["sessions"] if x["source"] == rec["source"] and x["song"] == rec["song"]]
        assert len(s) == 1, slug
        f = SEP.DATA / s[0]["path"]
        assert folder in (None, f), (slug, folder, f)
        folder = f
        a, b = rec["excerpt_start_frame"], rec["excerpt_end_frame"]
        cs, ce = SEP.window(rec["session_frames"], a, b, SEP.PAD_S * SR)
        out[slug] = {"stage_f": slug in pool, "crop": [a, b], "context": [cs, ce], "record": rec,
                     "crop_dir": str(crop)}
    return out, folder


def unity_sum(recs, folder):
    """The unity mono sum of every included mix track (union over the song's records)."""
    import numpy as np

    from analysis import io

    names = sorted({n for r in recs.values() for n in r["record"]["included_mix_tracks"]})
    tracks, rates = [], {}
    for n in names:
        au = io.load(folder / n)
        tracks.append(au.mono().astype(np.float32))
        rates[au.source_rate] = rates.get(au.source_rate, 0) + 1
    mix = np.zeros(max(len(t) for t in tracks), np.float64)
    for t in tracks:
        mix[:len(t)] += t
    return mix, names, rates


def global_candidates(mix, y, n=GLOBAL_PEAKS, sep=SR):
    """The n strongest whole-file GCC-PHAT offsets (session − preview frame) at least `sep` apart,
    with each peak's height in standard deviations of the correlation."""
    import numpy as np

    nfft = 1 << int(np.ceil(np.log2(len(mix) + len(y))))
    R = np.fft.rfft(mix, nfft) * np.conj(np.fft.rfft(y, nfft))
    cc = np.fft.irfft(R / (np.abs(R) + 1e-12), nfft)
    sd = float(np.std(cc)) + 1e-20
    out = []
    for k in np.argsort(cc)[::-1]:
        lag = int(k if k < nfft // 2 else k - nfft)
        if all(abs(lag - o) >= sep for o, _ in out):
            out.append((lag, round(float(cc[k] / sd), 1)))
        if len(out) == n:
            break
    return out


def refine(mix, seg, s0):
    """(start, r): the GCC-PHAT sample position of seg near session frame s0 (±REFINE), None when the
    peak sits on the search edge or the block falls outside the session."""
    import numpy as np

    blk = len(seg)
    lo, hi = max(0, s0 - REFINE), min(len(mix), s0 + blk + REFINE)
    if hi - lo < blk:
        return None, None
    ref = mix[lo:hi]
    d = gcc_phat(seg, ref, REFINE + (s0 - lo))
    s = lo + d
    if abs(s - s0) >= REFINE or s < 0 or s + blk > len(mix):
        return None, None
    return s, float(np.corrcoef(seg, mix[s:s + blk])[0, 1])


def align_one(mix, y, cands=()):
    """Per 4-s block: candidate positions from the block's envelope search and from the whole-file
    GCC-PHAT offsets `cands`, each refined to the sample; the one with the higher waveform r wins."""
    import numpy as np

    em = envelope(mix)
    blk, step = int(BLOCK_S * SR), int(STEP_S * SR)
    blocks = []
    for p0 in range(0, max(1, len(y) - blk + 1), step):
        seg = y[p0:p0 + blk]
        lvl = 10 * np.log10(np.mean(seg ** 2) + 1e-20)
        row = {"p0": p0, "p1": p0 + blk, "level_db": round(float(lvl), 1), "matched": False,
               "judged": bool(lvl > QUIET_DB), "offset": None, "r": None, "env_r": None, "source": None}
        if row["judged"]:
            k, er = ncc_lag(envelope(seg), em)
            best = None
            for src, s0 in [("envelope", k * HOP)] + [("global", p0 + c) for c, _ in cands]:
                s, r = refine(mix, seg, s0)
                if s is not None and (best is None or r > best[1]):
                    best = (s, r, src)
            if cands:                               # repeated audio: ties go to the main offset
                s, r = refine(mix, seg, p0 + cands[0][0])
                if (s is not None and abs(s - p0 - cands[0][0]) <= CLUSTER_GAP and best
                        and r >= best[1] - TIE_R):
                    best = (s, r, "global_main")
            row["env_r"] = round(er, 3)
            if best:
                row.update(offset=int(best[0] - p0), r=round(best[1], 3), source=best[2])
        blocks.append(row)
    return clusters(blocks)


def cmd_align():
    import numpy as np

    from analysis import io

    res = _load(IN / "alignment.json") or {}
    res["_method"] = __doc__.split("Alignment. ", 1)[1].strip()
    res["_conventions"] = {"offset_samples": "session frame − preview frame, both at 48 kHz",
                           "cluster_gap_samples": CLUSTER_GAP, "support_blocks": SUPPORT, "quiet_db": QUIET_DB}
    for song, files in preview_files().items():
        if not files:
            continue
        recs, folder = song_records(song)
        mix, names, rates = unity_sum(recs, folder)
        entry = res.get(song, {}) | {"session": str(folder), "n_tracks": len(names), "track_source_rates": rates,
                                     "session_s": round(len(mix) / SR, 2)}
        for kind, path in files:
            t = time.time()
            au = io.load(path)
            y = au.mono().astype(np.float64)
            cands = global_candidates(mix, y)
            blocks = align_one(mix, y, cands)
            sp = spans(blocks)
            sizes = {}
            for bl in blocks:
                if bl["matched"]:
                    sizes[bl["cluster"]] = sizes.get(bl["cluster"], 0) + 1
            cid = max(sizes, key=sizes.get) if sizes else None
            msp = spans(blocks, only=cid) if cid is not None else []
            judged_s = sum(1 for b in blocks if b["judged"]) * STEP_S
            crops = {}
            for slug, r in recs.items():
                fc, whole = covered(*r["crop"], msp)
                fx, wx = covered(*r["context"], msp)
                off = None if whole is None else offset_at(whole, (r["crop"][0] + r["crop"][1]) // 2 - whole["offset_samples"])
                chk = None if off is None else crop_check(mix, y, *r["crop"], off)
                ok = bool(chk and abs(chk["deviation_samples"]) <= CROP_OK_DEV and chk["peak_sd"] >= CROP_OK_SD)
                crops[slug] = {"stage_f": r["stage_f"], "crop_s": [round(v / SR, 2) for v in r["crop"]],
                               "crop_covered": round(fc, 3), "crop_in_main_span": whole is not None,
                               "context_covered": round(fx, 3), "context_in_main_span": wx is not None,
                               "offset_samples": off, "crop_gcc_check": chk, "covered": ok,
                               "crop_offset_samples": off + chk["deviation_samples"] if ok else None}
            main = max(msp, key=lambda s: s["n_blocks"]) if msp else None
            alt = [b for b in blocks if b["matched"] and b["cluster"] != cid]
            m = [b for b in blocks if b["matched"] and b["cluster"] == cid]
            u = [b for b in blocks if b["judged"] and not b["matched"] and b["r"] is not None]
            entry[kind] = {
                "file": path.name, "sha256": au.sha256, "source_rate": au.source_rate,
                "source_channels": au.source_channels,
                "sample_rate_handling": f"{au.source_rate} Hz, {au.source_channels} ch -> mono channel mean, "
                                        f"resampled to 48 kHz (analysis.io, resample_poly); session tracks "
                                        f"{rates} Hz -> 48 kHz the same way",
                "preview_s": round(len(y) / SR, 2),
                "offset_samples": None if main is None else main["offset_samples"],
                "offset_samples_at_source_rate": None if main is None else
                round(main["offset_samples"] * au.source_rate / SR),
                "correlation": {"median_r_matched_blocks": float(np.median([b["r"] for b in m])) if m else None,
                                "median_envelope_r_matched_blocks": float(np.median([b["env_r"] for b in m])) if m else None,
                                "median_r_unmatched_blocks": float(np.median([b["r"] for b in u])) if u else None,
                                "median_r_other_offset_blocks": float(np.median([b["r"] for b in alt])) if alt else None,
                                "note": "Pearson r of 4-s aligned waveforms (preview vs unity sum); the "
                                        "unmatched blocks' r is the no-match baseline"},
                "drift_ppm": None if main is None else main["drift_ppm"],
                "global_gcc_phat_candidates": [{"offset_samples": c, "peak_sd": h} for c, h in cands],
                "matched_spans": msp,
                "other_offset_spans": [x for x in sp if cid is None or abs(x["offset_samples"] - cid) > 4 * CLUSTER_GAP],
                "blocks": {"judged": sum(b["judged"] for b in blocks), "matched_main_offset": len(m),
                           "matched_other_offsets": len(alt), "total": len(blocks),
                           "other_offsets": sorted({b["cluster"] for b in alt})},
                "same_take": same_take(msp, judged_s, len(y) / SR,
                                       float(np.median([b["r"] for b in m])) if m else None,
                                       float(np.median([b["r"] for b in alt])) if alt else None,
                                       len(alt) / max(1, len(m) + len(alt))),
                "crops": crops, "wall_s": round(time.time() - t, 1)}
            _save(OUT / "blocks" / f"{song}-{kind}.json", blocks)
            print(song, kind, {k: entry[kind][k] for k in ("offset_samples", "same_take",
                                                           "drift_ppm", "blocks")}, flush=True)
            for x in msp:
                print("   ", x, flush=True)
        res[song] = entry
        _save(IN / "alignment.json", res)
    print("ALIGN DONE")


# --- separate ----------------------------------------------------------------------------------------

def stage_f_jobs():
    """[(song, slug, kind, offset)] for every stage F part whose crop lies inside one span."""
    al = _load(IN / "alignment.json")
    jobs = []
    for song, e in al.items():
        if song.startswith("_"):
            continue
        for kind in ("preview_mastered", "remix_mastered", "unmastered"):
            if kind not in e:
                continue
            for slug, c in e[kind]["crops"].items():
                if c["stage_f"] and c["covered"]:
                    jobs.append((song, slug, kind, c["crop_offset_samples"]))
    return jobs


def preview_context(song, kind, slug, off):
    """The preview's mono 48-kHz samples on the part's stored context window (session frames
    [cs, ce) shifted by the span's offset), zero where the preview has none; and the crop's index."""
    import numpy as np

    from analysis import io
    from learn import arm_a_mega53 as A

    al = _load(IN / "alignment.json")
    y = io.load(IN / al[song][kind]["file"]).mono().astype(np.float32)
    clog = _load(A.fdir("contexts", "log.json"))
    stored = np.load(A.fdir("contexts", f"{slug}.npy"))
    recs, _ = song_records(song)
    cs, ce = recs[slug]["context"]
    assert ce - cs == len(stored), (slug, ce - cs, len(stored))
    x = np.zeros(ce - cs, np.float32)
    p0, p1 = cs - off, ce - off
    a, b = max(0, p0), min(len(y), p1)
    x[a - p0:b - p0] = y[a:b]
    return x, clog[slug]["offset"], stored


def cmd_separate():
    import numpy as np

    from learn import separate as SEP

    d = OUT / "sep" / "mega53"
    d.mkdir(parents=True, exist_ok=True)
    log = _load(d / "log.json") or {}
    todo = [j for j in stage_f_jobs() if not (d / f"{j[1]}--{j[2]}.npy").exists()]
    if not todo:
        print("SEPARATE DONE")
        return
    model = SEP.guitar_separator("mega53")
    for song, slug, kind, off in todo:
        t = time.time()
        x, o, stored = preview_context(song, kind, slug, off)
        y = np.asarray(model(x), np.float32)[o:o + CROP]
        assert len(y) == CROP, (slug, len(y))
        np.save(d / f"{slug}--{kind}.npy", y)
        np.save(d / f"{slug}--{kind}-mix.npy", x[o:o + CROP])
        log[f"{slug}|{kind}"] = {"slug": slug, "song": song, "kind": kind, "offset_samples": off,
                                  "wall_s": round(time.time() - t, 1)}
        _save(d / "log.json", log)
        print(slug, kind, log[f"{slug}|{kind}"], flush=True)
    _save(d / "run.json", model.info() if hasattr(model, "info") else {})
    print("SEPARATE DONE")


def best_lag(x, ref, max_lag=4800):
    """(lag, normalised xcorr) maximising |xcorr| of x against ref (ref[t] ~ x[t − lag])."""
    import numpy as np

    n = 1 << int(np.ceil(np.log2(len(x) + len(ref))))
    cc = np.fft.irfft(np.fft.rfft(ref, n) * np.conj(np.fft.rfft(x, n)), n)
    cc = np.concatenate([cc[-max_lag:], cc[:max_lag + 1]]) / (np.linalg.norm(x) * np.linalg.norm(ref) + 1e-20)
    k = int(np.argmax(np.abs(cc)))
    return k - max_lag, float(cc[k])


def shift(x, lag):
    """x delayed by lag samples (zero fill)."""
    import numpy as np

    out = np.zeros_like(x)
    if lag >= 0:
        out[lag:] = x[:len(x) - lag]
    else:
        out[:lag] = x[-lag:]
    return out


# --- report ------------------------------------------------------------------------------------------

def cmd_report():
    """Per stage F part: (a) the raw amp track, (b) Mega-53 on our unity context (stored), (c) Mega-53
    on the aligned mastered preview, (u) on the unmastered mix where there is one. Gain-fitted SNR
    against (a) as aligned (the song's global offset), with the stem's own best lag (±100 ms; real
    mixes delay and flip single tracks), and after a held-out 2,048-tap least-squares FIR from the stem onto (a) (how much
    of the loss a linear EQ explains); LSD (1/3-octave long-term spectra after one gain, 80 Hz–12 kHz) between them."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import stereo_mix_check as SMC

    d = OUT / "sep" / "mega53"
    log = _load(d / "log.json")
    rows = {}
    for key, info in sorted(log.items()):
        slug, kind = info["slug"], info["kind"]
        part = A.f_part(slug)
        a = CR.mono(part["crop"] / "reference.wav")
        b = np.load(A.sep_crop("mega53", slug)).astype(np.float64)
        c = np.load(d / f"{slug}--{kind}.npy").astype(np.float64)
        um = CR.mono(part["crop"] / "mix.wav")
        pm = np.load(d / f"{slug}--{kind}-mix.npy").astype(np.float64)
        rows[key] = {
            "slug": slug, "band": A.pool_band(slug), "song": info["song"], "kind": kind,
            "snr_db": {"b_unity_stem": SMC.snr_db(b, a), "c_real_stem": SMC.snr_db(c, a)},
            "lag_vs_raw": {"b": best_lag(b, a), "c": best_lag(c, a)},
            "snr_db_lag_matched": {"b_unity_stem": SMC.snr_db(shift(b, best_lag(b, a)[0]), a),
                                   "c_real_stem": SMC.snr_db(shift(c, best_lag(c, a)[0]), a)},
            "snr_db_after_fir": {"b_unity_stem": SMC.snr_db(SMC.ls_fir_heldout(b, a), a),
                                 "c_real_stem": SMC.snr_db(SMC.ls_fir_heldout(c, a), a)},
            "lsd_db": {"a_vs_b": SMC.lsd_db(b, a), "a_vs_c": SMC.lsd_db(c, a), "b_vs_c": SMC.lsd_db(c, b)},
            "mix": {"r_unity_vs_real": float(np.corrcoef(um, pm)[0, 1]), "lsd_unity_vs_real": SMC.lsd_db(pm, um),
                    "rms_db_unity": float(10 * np.log10(np.mean(um ** 2))),
                    "rms_db_real": float(10 * np.log10(np.mean(pm ** 2)))},
        }
        print(key, json.dumps({k: v for k, v in rows[key].items() if k in ("snr_db", "lsd_db")}), flush=True)
    measures = (("snr_b", lambda r: r["snr_db"]["b_unity_stem"]), ("snr_c", lambda r: r["snr_db"]["c_real_stem"]),
                ("snr_c_minus_b", lambda r: r["snr_db"]["c_real_stem"] - r["snr_db"]["b_unity_stem"]),
                ("snr_lag_b", lambda r: r["snr_db_lag_matched"]["b_unity_stem"]),
                ("snr_lag_c", lambda r: r["snr_db_lag_matched"]["c_real_stem"]),
                ("snr_lag_c_minus_b", lambda r: r["snr_db_lag_matched"]["c_real_stem"] - r["snr_db_lag_matched"]["b_unity_stem"]),
                ("snr_fir_b", lambda r: r["snr_db_after_fir"]["b_unity_stem"]),
                ("snr_fir_c", lambda r: r["snr_db_after_fir"]["c_real_stem"]),
                ("lsd_a_b", lambda r: r["lsd_db"]["a_vs_b"]), ("lsd_a_c", lambda r: r["lsd_db"]["a_vs_c"]),
                ("lsd_b_c", lambda r: r["lsd_db"]["b_vs_c"]),
                ("lsd_c_minus_b", lambda r: r["lsd_db"]["a_vs_c"] - r["lsd_db"]["a_vs_b"]),
                ("mix_r", lambda r: r["mix"]["r_unity_vs_real"]), ("mix_lsd", lambda r: r["mix"]["lsd_unity_vs_real"]),
                ("mix_rms_real_minus_unity", lambda r: r["mix"]["rms_db_real"] - r["mix"]["rms_db_unity"]))
    summ = {}
    for group, kinds in (("mastered", ("preview_mastered", "remix_mastered")), ("unmastered", ("unmastered",))):
        sel = [r for r in rows.values() if r["kind"] in kinds]
        if not sel:
            continue
        g = {name: SMC.band_boot([(r["band"], get(r)) for r in sel]) | {"median_part": round(float(np.median([get(r) for r in sel])), 3)}
             for name, get in measures}
        g["parts"], g["c_lower_snr_parts"] = len(sel), sum(r["snr_db"]["c_real_stem"] < r["snr_db"]["b_unity_stem"] for r in sel)
        summ[group] = g
    _save(OUT / "report.json", {"summary": summ, "parts": rows})
    print(json.dumps(summ, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("align", "separate", "report"))
    a = ap.parse_args(argv)
    {"align": cmd_align, "separate": cmd_separate, "report": cmd_report}[a.cmd]()


if __name__ == "__main__":
    main()
