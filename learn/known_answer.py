"""Known-answer test songs, pilot B1 (`docs/known-answer-b1-plan.md`, part B's amendment of
`docs/clean-di-library-plan.md`). Development only; estimates with 90% band-clustered intervals,
no pass/fail bars.

    .venv/bin/python -m learn.known_answer plan                       # zero renders: DIs, sections, backings, leakage
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.known_answer truth    # menu scans, truth draws and renders (one process)
    .venv/bin/python -m learn.known_answer mix                        # the songs' mixes and contexts (zero renders)
    $TORCH_PY -m learn.known_answer separate                          # htdemucs on the contexts (CPU, behind the gate)
    $TORCH_PY -m learn.known_answer rebuild                           # C′ fold 2 on the stems and the oracle stems
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.known_answer search --shard i/3
    .venv/bin/python -m learn.known_answer report

Outputs go to ~/ndsp-presets/learn/known-answer/b1/. The recipe is arm A's adopted one, reused
unchanged from `learn/arm_a_mega53.py` (`recipe`, `objective`, `fallback_reason`, `peak_dbfs`).
The record for the judge is the truth rendered from the section's own slice of the DI, exactly as
every candidate is rendered, so the known answer is exact; `di_w` (the measure-DI treatment of the
whole DI) is the one DI level per track.

The pure parts (the primary-DI rule, eligibility, the section draw, the switch point, the backing
rules, the truth draw, the units, the counts, the sharding, the weighting and B2's size) are
unit-tested with fakes (`tests/test_known_answer.py`); the commands that render, separate or
rebuild are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/known-answer/b1"
REFS = HOME / "references"
SR = 48000
SEC_S = 10.0
TRIM_S = 0.25
LATENCY = 52
GRID_S = 5.0
CONTEXT_S = 30.0
CROSSFADE_S = 0.05
REST_MARGIN_S = 0.05
AMPS = ("pr12", "sw50r", "ac20")

SONGS = {
    "heather-jane": {"band": "Chris Coltraine", "song": "Heather Jane", "cls": "clean", "di_only": False,
                     "session": "datasets/cambridge/ChrisColtraine_HeatherJane_Full",
                     "second": "12_ElecGtr1DTDI.wav"},
    "bourbon": {"band": "Rebecca Haviland", "song": "Bourbon", "cls": "edge", "di_only": False,
                "session": "datasets/telefunken/Rebecca Haviland - Burbon", "second": "GTR 1 DI_TDP-1.wav"},
    "collide": {"band": "Rebecca Haviland", "song": "Collide With Me", "cls": "clean", "di_only": False,
                "session": "datasets/telefunken/Rebecaa Haviland - Collide With Me", "second": "GTR 2 DI_TDP-1.wav"},
    "apprehended": {"band": "The Apprehended", "song": "TheApprehended_StillFlyin_Full", "cls": "crunch",
                    "di_only": True,
                    "session": "datasets-set3/cambridge/TheApprehended_StillFlyin_Full/TheApprehended_StillFlyin_Full",
                    "second": "14_ElecGtr04DI.wav"},
}
BANDS = tuple(sorted({v["band"] for v in SONGS.values()}))
SECTION_SEED = 20261050
AMP_SEED = 20261051
TRUTH_SEED = 20261052
JITTER = 0.15
MAX_REDRAWS = 20
MIN_SECTIONS = 4
NOISY_FLAGS = {"hum", "hiss"}
DI_ONLY_G2B_DB = -7.9                 # multi-section step 1's median guitar-to-backing
SECOND_DOWN_DB = 6.0                  # The Apprehended's second guitar under the primary
LEAK_EXCESS = 0.05                    # part A's bleed threshold
OTHER_GUITAR = re.compile(r"(?i)elecgtr|gtr")
B2_H = 0.03
B2_SD_FLOOR = 0.069
CHI2_05 = {1: 0.00393, 2: 0.1026, 3: 0.3518, 4: 0.7107, 5: 1.1455}
T90 = {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833,
       10: 1.812, 12: 1.782, 15: 1.753, 20: 1.725, 30: 1.697, 60: 1.671}
# items: (kind, sections, mix) ; arm O shares s1/s2 across items 1, 2, 4, 5
ITEMS = {1: ("single", ("s1", "s2"), "v"), 2: ("single-novocals", ("s1", "s2"), "n"),
         3: ("switch", ("s3", "s4"), "v"), 4: ("two-guitars", ("s1", "s2"), "v"),
         5: ("no-other-guitars", ("s1", "s2"), "v")}
PRIMARY_ITEMS = (1, 3, 4)
IDENTIFIABLE = {"pr12": ("parameters/inputGain", "pr12Amp/pr12Treble", "pr12Amp/pr12Bass"),
                "sw50r": ("parameters/inputGain", "sw50rAmp/sw50rTreble", "sw50rAmp/sw50rMid", "sw50rAmp/sw50rBass"),
                "ac20": ("parameters/inputGain", "ac20Amp/ac20Cut")}
LEVEL_KNOBS = {"pr12": ("pr12Amp/pr12Volume",), "sw50r": ("sw50rAmp/sw50rVolume", "sw50rAmp/sw50rLevel"),
               "ac20": ("ac20Amp/ac20Volume", "ac20Amp/ac20Power")}
PER_SECTION_ARM = 3 * (1 + 2 * 55)    # warm-up + 2 directions × (52 search + probe + 2 judges), per amp
PER_SECTION_S = 3 * 2                 # S's warm-up and judge per amp


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def _seed(*xs):
    import hashlib

    return int.from_bytes(hashlib.sha256(json.dumps(list(xs)).encode()).digest()[:8], "big") >> 1


# --- the songs, DIs and sections -------------------------------------------------------------------

def eligible(rows):
    """Section starts for a DI: its non-overlapping clean ones; when fewer than MIN_SECTIONS, the
    greedy non-overlapping ones among the activity-passing rows flagged only hum or hiss (or none).
    -> (starts, noisy)."""
    clean = sorted(r["start_s"] for r in rows if r.get("disjoint"))
    if len(clean) >= MIN_SECTIONS:
        return clean, False
    ok = sorted(r["start_s"] for r in rows if set(r.get("flags") or []) <= NOISY_FLAGS)
    out, end = [], -math.inf
    for s in ok:
        if s >= end:
            out.append(s)
            end = s + SEC_S
    return out, True


def primary_di(rows_by_di):
    """The DI with the most clean non-overlapping sections, then the most eligible, then by name."""
    def key(d):
        rows = rows_by_di[d]
        return (-sum(1 for r in rows if r.get("disjoint")), -len(eligible(rows)[0]), d)

    return sorted(rows_by_di, key=key)[0]


def boundaries(n_s, grid_s=GRID_S):
    return [k * grid_s for k in range(1, int(n_s // grid_s) + 1)]


def rests_at(play, b_s, hop_s, margin_s=REST_MARGIN_S):
    """No playing frame whose centre lies within ±margin of b."""
    lo = int(math.floor((b_s - margin_s) / hop_s))
    hi = int(math.ceil((b_s + margin_s) / hop_s))
    return not any(play[max(0, lo):max(0, hi + 1)])


def switch_point(starts, n_s, play, hop_s):
    """(switch time, rests): the grid boundary nearest the middle with at least one eligible section
    wholly on each side; among those, the nearest that rests, else the nearest (crossfade)."""
    mid = n_s / 2
    cands = [b for b in boundaries(n_s) if any(s + SEC_S <= b for s in starts) and any(s >= b for s in starts)]
    if not cands:
        raise ValueError("no boundary leaves an eligible section on each side")
    cands.sort(key=lambda b: (abs(b - mid), b))
    for b in cands:
        if rests_at(play, b, hop_s):
            return b, True
    return cands[0], False


def draw_sections(starts, switch_s, song):
    """{s1..s4: start}: s3 before the switch, s4 after, s1 and s2 from the rest (seeded)."""
    rng = random.Random(_seed(SECTION_SEED, song))
    before = [s for s in starts if s + SEC_S <= switch_s]
    after = [s for s in starts if s >= switch_s]
    s3, s4 = rng.choice(before), rng.choice(after)
    rest = [s for s in starts if s not in (s3, s4)]
    if len(rest) < 2:
        raise ValueError(f"{song}: fewer than 4 eligible sections")
    s1, s2 = sorted(rng.sample(rest, 2))
    return {"s1": s1, "s2": s2, "s3": s3, "s4": s4}


def draw_amps(song):
    rng = random.Random(_seed(AMP_SEED, song))
    a1 = rng.choice(AMPS)
    others = [a for a in AMPS if a != a1]
    return {"P1": a1, "P2": rng.choice(others), "Q": rng.choice(others)}


def classes_for(cls):
    """(P1, P2, Q) classes: P2 crunch after clean or edge, clean after crunch; Q as P1."""
    return cls, ("clean" if cls == "crunch" else "crunch"), cls


def s_class(cls):
    """The starting preset's class: edge starts from crunch (review item 16)."""
    return "crunch" if cls in ("edge", "crunch") else "clean"


def in_class(target, m, line):
    """Amendment 1, item 6: clean = the classifier's clean; crunch = crunch or high-gain whose level
    slope is not below `line` (the crunch S's own slope on that section); edge = either."""
    cls, slope = m.get("class"), m.get("slope")
    clean = cls == "clean"
    crunch = cls in ("crunch", "high-gain") and slope is not None and line is not None and slope >= line
    return {"clean": clean, "crunch": crunch, "edge": clean or crunch}[target]


def pools(scan, line):
    """{clean: [...], crunch: [...]}: the scanned presets (not the starting presets) in each class."""
    out = {"clean": [], "crunch": []}
    for name, m in sorted(scan.items()):
        if m.get("is_start"):
            continue
        for c in out:
            if in_class(c, m, line):
                out[c].append(name)
    return out


def role_amp(drawn, usable, song, role):
    """The role's amp: the drawn one if its pool is usable, else a seeded draw among the others that
    are; None when none is."""
    if drawn in usable:
        return drawn
    rest = [a for a in AMPS if a != drawn and a in usable]
    return random.Random(_seed(AMP_SEED, song, role, "redraw")).choice(rest) if rest else None


MAX_PRESETS = 5
SELF_MAX = 0.1                        # the truth's self-distance, as a share of S's (integrity, item 4)


def is_vocal(name):
    n = pathlib.PurePosixPath(name).name.lower()
    return "vox" in n or "vocal" in n


def backing(files, own, is_di, leaking=(), vocals=True, other_guitars=True):
    """The backing's tracks: every file, less guitar DIs, less the rendered DIs' own tracks, less
    leaking tracks; optionally less vocals and less every other guitar track."""
    out = []
    for f in files:
        if is_di(f) or f in own or f in leaking:
            continue
        if not vocals and is_vocal(f):
            continue
        if not other_guitars and OTHER_GUITAR.search(pathlib.PurePosixPath(f).stem) and not re.search(r"(?i)bass", f):
            continue
        out.append(f)
    return out


def items_for(song):
    return [k for k in ITEMS if k != 5 or SONGS[song]["di_only"]]


def units(plan):
    """[(song, item, section label, arm)] to search; arm O once per (song, section)."""
    out = []
    for song in SONGS:
        if song not in plan["songs"]:
            continue
        for it in items_for(song):
            for s in ITEMS[it][1]:
                out.append((song, it, s, "A"))
        for s in ("s1", "s2", "s3", "s4"):
            out.append((song, 0, s, "O"))
    return out


def expected_renders(plan):
    u = units(plan)
    secs = {(x[0], x[2]) for x in u}
    return len(u) * PER_SECTION_ARM + len(secs) * PER_SECTION_S


def groups(plan):
    """(song, section label, amp) groups: S and every unit on that section and amp."""
    return sorted({(x[0], x[2], a) for x in units(plan) for a in AMPS})


def shard_groups(gs, shard):
    k, n = shard
    return [g for j, g in enumerate(gs) if j % n == k]


def truth_of(song, label):
    """Which truth a scored section has: P2 for s4 (after the switch), else P1."""
    return "P2" if label == "s4" else "P1"


# --- the truth draw (pure) ---------------------------------------------------------------------------

def jitter_truth(rng, dims, settings, fmt, offset=JITTER, fixed=None):
    """Every continuous dimension moved by a uniform offset within ±offset (unit scale), clipped;
    switches and mics kept; `fixed` {(module, key): unit} set instead of jittered."""
    x = dict(settings)
    for d in dims:
        k = (d.module, d.key)
        if d.kind not in ("cont", "log"):
            continue
        if fixed and k in fixed:
            u = fixed[k]
        else:
            u = min(1.0, max(0.0, d.to_unit(settings.get(k, d.lo)) + rng.uniform(-offset, offset)))
        x[k] = fmt(d.from_unit(u))
    return x


def edge_gain_range(crunch_units):
    """The lower half of the measured-crunch presets' input-gain values: (min, median)."""
    v = sorted(crunch_units)
    if not v:
        raise ValueError("no measured-crunch preset")
    m = v[(len(v) - 1) // 2] if len(v) % 2 else 0.5 * (v[len(v) // 2 - 1] + v[len(v) // 2])
    return v[0], m


# --- the readout (pure) ------------------------------------------------------------------------------

def band_interval(values_by_band):
    means = [sum(v) / len(v) for v in values_by_band.values() if v]
    n = len(means)
    if n == 0:
        return {"mean": None, "lo": None, "hi": None, "bands": 0, "sd": None}
    m = sum(means) / n
    if n < 2:
        return {"mean": m, "lo": None, "hi": None, "bands": n, "sd": None}
    sd = math.sqrt(sum((x - m) ** 2 for x in means) / (n - 1))
    h = T90.get(n - 1, 1.645) * sd / math.sqrt(n)
    return {"mean": m, "lo": m - h, "hi": m + h, "bands": n, "sd": sd}


def weighted(rows):
    """rows: [(band, song, unit key, value)]: unit → song → band means, then the interval."""
    by_song = {}
    for band, song, key, v in rows:
        by_song.setdefault((band, song), {}).setdefault(key, []).append(v)
    by_band = {}
    for (band, song), us in by_song.items():
        ms = [sum(v) / len(v) for v in us.values()]
        by_band.setdefault(band, []).append(sum(ms) / len(ms))
    return band_interval(by_band)


def _t90(df):
    ks = sorted(T90)
    for k in ks:
        if df <= k:
            return T90[k]
    return 1.645


def b2_songs(sd, bands, h=B2_H, floor=B2_SD_FLOOR):
    """(upper 90% SD bound, n) for B2: n = (t · max(upper, floor) / h)², iterated in t."""
    if sd is None or bands < 2:
        up = None
        s = floor
    else:
        df = bands - 1
        up = sd * math.sqrt(df / CHI2_05[min(df, max(CHI2_05))])
        s = max(up, floor)
    n = 2
    for _ in range(50):
        n2 = math.ceil((_t90(n - 1) * s / h) ** 2)
        if n2 == n:
            break
        n = max(2, n2)
    return up, n


# --- I/O helpers -------------------------------------------------------------------------------------

def session_dir(song):
    return REFS / SONGS[song]["session"]


def load_mono(path, sr_out=SR):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1).astype(np.float64)
    if sr != sr_out:
        g = math.gcd(sr_out, sr)
        x = resample_poly(x, sr_out // g, sr // g)
    return x


def lufs_masked(x, mask_frames, hop):
    """Integrated loudness of the frames marked playing (concatenated)."""
    import numpy as np
    import pyloudnorm

    seg = [x[k * hop:(k + 1) * hop] for k, m in enumerate(mask_frames) if m]
    if not seg:
        return -70.0
    v = pyloudnorm.Meter(SR).integrated_loudness(np.concatenate(seg))
    return float(v) if np.isfinite(v) else -70.0


def play_mask(di, hop=SR // 10):
    """100-ms frames within 40 dB of the DI's loudest (part A's playing rule, 100-ms frames)."""
    import numpy as np

    n = len(di) // hop
    e = 10 * np.log10(np.mean(di[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-30)
    return e >= e.max() - 40.0


# --- plan --------------------------------------------------------------------------------------------

def cmd_plan(_args):
    """Zero renders: per song the DIs, the primary, sections, the switch point, and the backings with
    the leakage check against the rendered DIs' own tracks."""
    import numpy as np

    from learn import clean_di as CD

    man = json.loads(CD.OUT.joinpath("manifest.json").read_text())
    inv = json.loads(CD.OUT.joinpath("inventory.json").read_text())
    plan = {"songs": {}, "manifest_sha256": None}
    bins = CD.bleed_bins()
    for song, spec in SONGS.items():
        sess = session_dir(song)
        dis = [d for d in inv["dis"] if d["band"] == spec["band"] and pathlib.Path(d["path"]).parent == sess]
        assert dis and all(d["split"] == "known_answer" for d in dis), song
        rows_by = {d["id"]: [r for r in man["sections"] if r["di"] == d["id"]] for d in dis}
        prim = primary_di(rows_by)
        starts, noisy = eligible(rows_by[prim])
        prec = next(d for d in dis if d["id"] == prim)
        srec = next(d for d in dis if pathlib.Path(d["path"]).name == spec["second"])
        assert srec["id"] != prim, song
        di = load_mono(prec["path"])
        n_s = len(di) / SR
        pm = play_mask(di)
        b, rests = switch_point(starts, n_s, pm, 0.1)
        secs = draw_sections(starts, b, song)
        files = sorted(f.name for f in sess.glob("*.wav"))
        own = {"primary": prec.get("own") or [], "second": srec.get("own") or []}
        leaks, readings = {"primary": [], "second": []}, {}
        for role, tracks in own.items():
            for o in tracks:
                a = load_mono(sess / o, CD.BLEED_SR)
                Xa = CD.stft16(a)
                pa = 10 * np.log10(np.mean(np.abs(Xa) ** 2, 1) + 1e-20)
                rows_ = pa >= pa.max() - CD.OTHER_ACTIVE_DB
                for t in backing(files, set(own["primary"]) | set(own["second"]), CD.is_guitar_di):
                    y = load_mono(sess / t, CD.BLEED_SR)
                    n = min(len(y), len(a))
                    Y = CD.stft16(y[:n])
                    msc, bias = CD.coherence(Y, Xa[:len(Y)], rows_[:len(Y)], bins)
                    e = round(float(msc - bias), 4)
                    readings.setdefault(role, {})[t] = max(readings.get(role, {}).get(t, -1.0), e)
            leaks[role] = sorted(t for t, e in readings.get(role, {}).items() if e > LEAK_EXCESS)
        flags = {k: next((r["flags"] for r in rows_by[prim] if abs(r["start_s"] - v) < 1e-6), None)
                 for k, v in secs.items()}
        plan["songs"][song] = {
            **spec, "primary": prim, "primary_path": prec["path"], "primary_part": prec["part"],
            "second": srec["id"], "second_path": srec["path"], "own": own, "noisy_di": noisy,
            "eligible": starts, "sections": secs, "section_flags": flags, "switch_s": b, "switch_rests": rests,
            "length_s": n_s, "files": files, "leak_readings": readings, "leaking": leaks,
            "amps": draw_amps(song), "classes": dict(zip(("P1", "P2", "Q"), classes_for(spec["cls"])))}
        print(song, prim, "noisy" if noisy else "clean", secs, "switch", b, "rests" if rests else "crossfade",
              "leaking", leaks, flush=True)
    from learn import pretrain_set as PS

    plan["manifest_sha256"] = PS.file_sha256(CD.OUT / "manifest.json")
    plan["expected_renders_search"] = expected_renders(plan)
    _save(OUT / "plan.json", plan)
    print("plan: expected search renders", plan["expected_renders_search"])
    print("PLAN DONE")


def load_plan():
    p = _load(OUT / "plan.json")
    if p is None:
        raise SystemExit("run `plan` first")
    return p


# --- truth -------------------------------------------------------------------------------------------

def di_w(path):
    """The measure-DI treatment of the whole DI (the one DI level per track)."""
    from learn import song_bank as B

    return B.measure(load_mono(path)).astype("float64")


def render_trim(rr, x, sel, settings, pre_s=TRIM_S):
    """Render with `pre_s` of silence prepended, trimmed off (the raw output, latency kept)."""
    import numpy as np

    pre = int(pre_s * SR)
    y = np.asarray(rr.render(np.concatenate([np.zeros(pre, np.float32), x.astype(np.float32)]), sel, settings),
                   np.float64)
    y = y.mean(axis=1) if y.ndim == 2 else y
    return y[pre:pre + len(x)]


def classify_render(y, di):
    from learn import pretrain_set as PS

    return PS.gain_class(y, di)


def mono(y):
    import numpy as np

    y = np.asarray(y, np.float64)
    return y.mean(axis=1) if y.ndim == 2 else y


def sec_slice(start_s, sr=SR):
    a = int(round(start_s * sr))
    return slice(a, a + int(SEC_S * sr))


def scan_amp(rr, menu, amp, d1):
    """Every dry factory preset of the amp rendered once on the section and classed."""
    import numpy as np

    from learn import knob_ceiling as K

    starts = {K.START[c][amp] for c in ("clean", "crunch")}
    out = {}
    for name in sorted(menu[amp]):
        sel, x = menu[amp][name]
        y = mono(rr.render(d1.astype(np.float32), sel, x))
        out[name] = {**classify_render(np.asarray(y, np.float64), d1), "is_start": name in starts}
    return out


def disk_guard():
    from learn import pretrain_set as PS

    if not PS.disk_ok():
        print("DISK GUARD", round(PS.free_gb(), 1), flush=True)
        raise SystemExit(4)


def cmd_truth(_args):
    """Menu scans, the truth draws with their class checks, whole-track truths, section records, the
    self-distance and convention-floor checks."""
    import numpy as np
    import soundfile as sf

    from learn import arm_a_mega53 as AM
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import song_bank as B

    plan = load_plan()
    LO._wait_cap()
    rr = AM.renderer()
    tdir = OUT / "truth"
    tdir.mkdir(parents=True, exist_ok=True)
    state = _load(tdir / "truth.json") or {}
    try:
        menu = rr.menu()
        for song, sp in plan["songs"].items():
            if state.get(song, {}).get("done"):
                continue
            disk_guard()
            st = state.setdefault(song, {"scans": {}, "draws": {}, "renders": 0})
            n0 = rr.count
            dw = {"primary": di_w(sp["primary_path"]), "second": di_w(sp["second_path"])}
            s1 = sp["sections"]["s1"]
            d_of = {"primary": dw["primary"][sec_slice(s1)], "second": dw["second"][sec_slice(s1)]}
            for role in ("P1", "P2", "Q"):
                if role in st["draws"]:
                    continue
                di_role = "second" if role == "Q" else "primary"
                d1 = d_of[di_role]
                cls = sp["classes"][role]
                pool_cls = "crunch" if cls == "edge" else cls
                avoid = {st["draws"]["P1"]["amp"]} if role != "P1" and "P1" in st["draws"] else set()
                usable, lines = [], {}
                for amp in [sp["amps"][role]] + [a for a in AMPS if a != sp["amps"][role]]:
                    if amp in avoid:
                        continue
                    key = f"{amp}|{di_role}"
                    if key not in st["scans"]:
                        st["scans"][key] = scan_amp(rr, menu, amp, d1)
                        _save(tdir / "truth.json", state)
                    line = st["scans"][key][K.START["crunch"][amp]].get("slope")
                    lines[amp] = line
                    if pools(st["scans"][key], line)[pool_cls]:
                        usable.append(amp)
                    if amp == sp["amps"][role] and usable:
                        break
                amp = role_amp(sp["amps"][role], usable, song, role)
                if amp is None:
                    raise SystemExit(f"{song} {role}: no measured-{pool_cls} preset on any amp")
                scan, line = st["scans"][f"{amp}|{di_role}"], lines[amp]
                cands = pools(scan, line)[pool_cls]
                rng = random.Random(_seed(TRUTH_SEED, song, role))
                gain_dim = next(d for d in K.space(amp) if d.key == "inputGain")
                if cls == "edge":
                    lo, hi = edge_gain_range([gain_dim.to_unit(menu[amp][n][1].get(("parameters", "inputGain"),
                                                                                  gain_dim.lo)) for n in cands])
                log, chosen = [], None
                for _ in range(MAX_PRESETS):
                    name = rng.choice(cands)
                    sel, base = menu[amp][name]
                    for _ in range(MAX_REDRAWS):
                        fixed = {("parameters", "inputGain"): rng.uniform(lo, hi)} if cls == "edge" else None
                        x = jitter_truth(rng, K.space(amp, base), base, K.fmt, fixed=fixed)
                        y = mono(rr.render(d1.astype(np.float32), sel, x))
                        m = classify_render(np.asarray(y, np.float64), d1)
                        log.append({"preset": name, **m})
                        if in_class(cls, m, line):
                            chosen = {"preset": name, "select": sel, "settings": LO.sdict(x), "class_measured": m,
                                      "line": line, "draws": len(log)}
                            break
                    if chosen:
                        break
                if chosen is None:
                    raise SystemExit(f"{song} {role}: no truth in class after {len(log)} draws")
                st["draws"][role] = {**chosen, "amp": amp, "class": cls, "amp_drawn": sp["amps"][role], "log": log}
                _save(tdir / "truth.json", state)
            for role, di_role in (("P1", "primary"), ("P2", "primary"), ("Q", "second")):
                f = tdir / f"{song}-{role}.flac"
                if f.exists():
                    continue
                dr = st["draws"][role]
                y = render_trim(rr, dw[di_role], dr["select"], LO.tdict(dr["settings"]))
                y = np.concatenate([y[LATENCY:], np.zeros(LATENCY)])         # latency-compensated for the mix
                pk = float(np.max(np.abs(y))) or 1.0
                sf.write(str(f), (y / pk * 0.99).astype(np.float32), SR, subtype="PCM_24")
                st.setdefault("peaks", {})[role] = pk
                _save(tdir / "truth.json", state)
            menu_S = {}
            for lab, start in sp["sections"].items():
                role = truth_of(song, lab)
                dr = st["draws"][role]
                tx = LO.tdict(dr["settings"])
                d_ = dw["primary"][sec_slice(start)]
                rec = np.asarray(rr.render(d_.astype(np.float32), dr["select"], tx), np.float64)
                rec = rec.mean(axis=1) if rec.ndim == 2 else rec
                np.save(tdir / f"{song}-{lab}-record.npy", rec.astype(np.float32))
                np.save(tdir / f"{song}-{lab}-di.npy", d_.astype(np.float32))
                chk = st.setdefault("checks", {}).setdefault(lab, {})
                chk["delta_lufs"] = LO.lufs(d_) - LO.REBUILD_LUFS
                # item 4: the truth through the judge's own path, against S on the truth's amp
                y_self = mono(rr.render(d_.astype(np.float32), dr["select"], tx))
                sel_s, S = menu[dr["amp"]][K.START[s_class(dr["class"])][dr["amp"]]]
                menu_S[lab] = (sel_s, S)
                j_self = K.judge(rec, y_self, d_, LATENCY)
                j_S = K.judge(rec, mono(rr.render(d_.astype(np.float32), sel_s, S)), d_, LATENCY)
                chk["self"], chk["S_truth_amp"] = j_self, j_S
                bad = [h for h in ("A", "B") if not (j_self[h] < SELF_MAX * j_S[h])]
                if bad:
                    _save(tdir / "truth.json", state)
                    raise SystemExit(f"{song} {lab}: the truth's self-distance {j_self} is not under "
                                     f"{SELF_MAX} of S's {j_S} (halves {bad}): exactness is broken")
                # item 3: the convention floor (the truth on the per-section measure DI)
                dm = B.measure(d_)
                chk["convention_floor"] = K.judge(rec, mono(rr.render(dm.astype(np.float32), dr["select"], tx)), dm, LATENCY)
                # the whole-track truth's slice against the record
                whole, _ = sf.read(str(tdir / f"{song}-{role}.flac"), dtype="float64")
                whole = whole / 0.99 * st["peaks"][role]
                ws = np.concatenate([np.zeros(LATENCY), whole])[sec_slice(start)]       # back to raw latency
                chk["whole_vs_record"] = K.judge(rec, ws, d_, LATENCY)
                _save(tdir / "truth.json", state)
            st["renders"] = st.get("renders", 0) + rr.count - n0
            st["done"] = True
            _save(tdir / "truth.json", state)
            print(song, "truth done", {r: (st["draws"][r]["preset"], st["draws"][r]["amp"]) for r in st["draws"]},
                  "renders", st["renders"], flush=True)
    finally:
        rr.close()
    print("TRUTH DONE")


# --- mix ---------------------------------------------------------------------------------------------

def level_gain_db(truth, ref_tracks_sum, mask, hop):
    """dB that brings the truth's loudness over the playing frames to the reference's there."""
    return lufs_masked(ref_tracks_sum, mask, hop) - lufs_masked(truth, mask, hop)


def splice(a, b, at, rests, sr=SR):
    """a before `at` seconds, b after; a 50-ms linear crossfade unless the DI rests there."""
    import numpy as np

    k = int(round(at * sr))
    out = a.copy()
    if rests:
        out[k:] = b[k:]
        return out
    h = int(CROSSFADE_S * sr / 2)
    w = np.linspace(0, 1, 2 * h)
    out[k + h:] = b[k + h:]
    out[k - h:k + h] = a[k - h:k + h] * (1 - w) + b[k - h:k + h] * w
    return out


def cmd_mix(_args):
    """Per song and item the full mix, then 30-s contexts around each scored section, and the oracle
    stems (the primary truth at its mix level)."""
    import numpy as np
    import soundfile as sf

    from learn import clean_di as CD

    plan = load_plan()
    tr = _load(OUT / "truth" / "truth.json")
    mdir = OUT / "mix"
    mdir.mkdir(parents=True, exist_ok=True)
    log = _load(mdir / "log.json") or {}
    hop = SR // 10
    for song, sp in plan["songs"].items():
        if song in log:
            continue
        sess = session_dir(song)
        st = tr[song]

        def truth(role):
            y, _ = sf.read(str(OUT / "truth" / f"{song}-{role}.flac"), dtype="float64")
            return y / 0.99 * st["peaks"][role]

        def tracks(names, n):
            s = np.zeros(n)
            for t in names:
                x = load_mono(sess / t)[:n]
                s[:len(x)] += x
            return s

        dprim = load_mono(sp["primary_path"])
        dsec = load_mono(sp["second_path"])
        n = len(dprim)
        mp, ms = play_mask(dprim, hop), play_mask(dsec[:n], hop)
        own_all = set(sp["own"]["primary"]) | set(sp["own"]["second"])
        is_di = CD.is_guitar_di
        leak_p, leak_s = sp["leaking"]["primary"], sp["leaking"]["second"]
        P1, P2, Q = (truth(r)[:n] for r in ("P1", "P2", "Q"))
        P1 = np.pad(P1, (0, n - len(P1)))
        P2 = np.pad(P2, (0, n - len(P2)))
        Q = np.pad(Q, (0, n - len(Q)))
        k_switch = int(round(sp["switch_s"] * SR))
        row = {"tracks": {}, "gains_db": {}}
        if sp["di_only"]:
            bv = tracks(backing(sp["files"], set(sp["own"]["primary"]), is_di, leak_p), n)
            g1 = lufs_masked(bv, mp, hop) + DI_ONLY_G2B_DB - lufs_masked(P1, mp, hop)
            m2 = mp.copy()
            m2[:k_switch // hop] = False
            g2 = lufs_masked(bv, m2, hop) + DI_ONLY_G2B_DB - lufs_masked(P2, m2, hop)
            gq = g1 - SECOND_DOWN_DB + lufs_masked(P1, mp, hop) - lufs_masked(Q, ms, hop)
        else:
            refp = tracks(sp["own"]["primary"], n)
            refs = tracks(sp["own"]["second"], n)
            g1 = level_gain_db(P1, refp, mp, hop)
            m2 = mp.copy()
            m2[:k_switch // hop] = False
            g2 = level_gain_db(P2, refp, m2, hop)
            gq = level_gain_db(Q, refs, ms, hop)
        row["gains_db"] = {"P1": g1, "P2": g2, "Q": gq}
        G1 = P1 * 10 ** (g1 / 20)
        Gsw = splice(G1, P2 * 10 ** (g2 / 20), sp["switch_s"], sp["switch_rests"])
        GQ = Q * 10 ** (gq / 20)
        for it in items_for(song):
            kind, labs, mixk = ITEMS[it]
            own = set(sp["own"]["primary"]) | (set(sp["own"]["second"]) if it == 4 else set())
            leaking = set(leak_p) | (set(leak_s) if it == 4 else set())
            names = backing(sp["files"], own, is_di, leaking, vocals=(mixk == "v"), other_guitars=(it != 5))
            back = tracks(names, n)
            if it == 1:
                row["g2b_at_unity_db"] = lufs_masked(G1, mp, hop) - lufs_masked(back, mp, hop)
            guitar = Gsw if it == 3 else (G1 + GQ if it == 4 else G1)
            mix = back + guitar
            row["tracks"][str(it)] = names
            for lab in labs:
                start = sp["sections"][lab]
                c0 = max(0.0, min(start + SEC_S / 2 - CONTEXT_S / 2, n / SR - CONTEXT_S))
                a, b = int(round(c0 * SR)), int(round(c0 * SR)) + int(CONTEXT_S * SR)
                np.save(mdir / f"{song}-{it}-{lab}-context.npy", mix[a:b].astype(np.float32))
                row.setdefault("offsets", {})[f"{it}-{lab}"] = int(round(start * SR)) - a
        for lab, start in sp["sections"].items():
            g = Gsw if lab in ("s3", "s4") else G1
            np.save(mdir / f"{song}-{lab}-oracle.npy", g[sec_slice(start)].astype(np.float32))
        dropped = sorted(set(leak_p) | set(leak_s))
        row["leak_dropped"] = dropped
        full = tracks(backing(sp["files"], own_all, is_di), n)
        kept = tracks(backing(sp["files"], own_all, is_di, dropped), n)
        row["leak_power_share_dropped"] = 1 - float(np.sum(kept ** 2)) / max(float(np.sum(full ** 2)), 1e-30)
        log[song] = row
        _save(mdir / "log.json", log)
        print(song, "mixes", row["gains_db"], "dropped", dropped, flush=True)
    print("MIX DONE")


# --- separate, rebuild -------------------------------------------------------------------------------

def contexts(plan):
    """[(song, item, label)] of every arm-A context."""
    return [(s, it, lab) for s in plan["songs"] for it in items_for(s) for lab in ITEMS[it][1]]


def cmd_separate(_args):
    import os

    import numpy as np

    from learn import arm_a_mega53 as AM
    from learn import local_objective_1c as C

    plan = load_plan()
    log = _load(OUT / "mix" / "log.json")
    d = OUT / "sep"
    d.mkdir(parents=True, exist_ok=True)
    todo = [c for c in contexts(plan) if not (d / f"{c[0]}-{c[1]}-{c[2]}.npy").exists()]
    if not todo:
        print("SEPARATE DONE")
        return
    os.environ["DEVICE"] = "cpu"
    AM.wait_separation_gate(C.MEM_GATE_PRUNED_GB)
    from learn.separate import GuitarSeparator

    model = GuitarSeparator()
    if model.device != "cpu":
        raise SystemExit(f"htdemucs runs on {model.device}, not the CPU")
    for song, it, lab in todo:
        AM.wait_separation_gate(C.MEM_GATE_PRUNED_GB, memory=False)
        x = np.load(OUT / "mix" / f"{song}-{it}-{lab}-context.npy")
        y = np.asarray(model(x), np.float32)
        off = log[song]["offsets"][f"{it}-{lab}"]
        np.save(d / f"{song}-{it}-{lab}.npy", y[off:off + int(SEC_S * SR)])
        print("separated", song, it, lab, flush=True)
    print("SEPARATE DONE")


def assert_cprime_unseen(pool_bands, bands=BANDS, songs=SONGS):
    keys = set(bands) | {f"{'telefunken' if 'telefunken' in v['session'] else 'cambridge'}/{v['song']}"
                         for v in songs.values()}
    hit = keys & set(pool_bands)
    if hit:
        raise AssertionError(f"C′ fold 2 trained on {sorted(hit)}")


def cmd_rebuild(_args):
    import numpy as np
    import torch

    from learn import di_fine_structure as DF
    from learn import direc as D
    from learn import song_settings as SS
    from learn.direc_check import to_lufs

    plan = load_plan()
    path = SS.cprime(2)
    if not SS.net_ready(path):
        raise SystemExit(f"{path} is not final")
    assert_cprime_unseen(DF.train_pool_bands(2, [DF.MODELS / c for c in DF.CACHES]))
    net = D.load_model(path).eval()
    d = OUT / "rebuilt"
    d.mkdir(parents=True, exist_ok=True)
    srcs = [(f"{s}-{it}-{lab}", OUT / "sep" / f"{s}-{it}-{lab}.npy") for s, it, lab in contexts(plan)]
    srcs += [(f"{s}-O-{lab}", OUT / "mix" / f"{s}-{lab}-oracle.npy") for s in plan["songs"] for lab in ("s1", "s2", "s3", "s4")]
    for name, src in srcs:
        out = d / f"{name}.npy"
        if out.exists():
            continue
        x = np.load(src).astype(np.float32)
        y = D.rebuild(net, x, device=torch.device("cpu")).astype(np.float64)
        np.save(out, to_lufs(y))
        print("rebuilt", name, flush=True)
    print("REBUILD DONE")


# --- search ------------------------------------------------------------------------------------------

def stem_of(song, it, lab, arm):
    import numpy as np

    if arm == "O":
        return np.load(OUT / "mix" / f"{song}-{lab}-oracle.npy").astype(np.float64)
    return np.load(OUT / "sep" / f"{song}-{it}-{lab}.npy").astype(np.float64)


def rebuilt_of(song, it, lab, arm):
    import numpy as np

    return np.load(OUT / "rebuilt" / (f"{song}-O-{lab}.npy" if arm == "O" else f"{song}-{it}-{lab}.npy"))


def result_path(song, it, lab, arm, amp, search):
    return OUT / "results" / song / f"{arm}-{it}-{lab}-{amp}-{search}.json"


def cmd_search(args):
    import numpy as np

    from learn import arm_a_mega53 as AM
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    plan = load_plan()
    tr = _load(OUT / "truth" / "truth.json")
    us = units(plan)
    mine = shard_groups(groups(plan), args.shard)
    LO._wait_cap()
    rr = AM.renderer()
    try:
        menu = rr.menu()
        last = None
        for song, lab, amp in mine:
            if amp != last:
                disk_guard()
                LO._wait_cap()
                last = amp
            sp = plan["songs"][song]
            role = truth_of(song, lab)
            cls = tr[song]["draws"][role]["class"]
            sel, S = menu[amp][K.START[s_class(cls)][amp]]
            di = np.load(OUT / "truth" / f"{song}-{lab}-di.npy").astype(np.float64)
            di32 = di.astype(np.float32)
            rec = np.load(OUT / "truth" / f"{song}-{lab}-record.npy").astype(np.float64)
            sp_ = OUT / "results" / song / f"S-{lab}-{amp}.json"
            if not sp_.exists():
                n0 = rr.count
                rr.render(di32, sel, S)
                y = mono(rr.render(di32, sel, S))
                _save(sp_, {"judge": K.judge(rec, y, di, LATENCY), "renders": rr.count - n0,
                            "settings": LO.sdict(S), "class_S": s_class(cls)})
            for (s_, it, l_, arm) in us:
                if s_ != song or l_ != lab:
                    continue
                if all(result_path(song, it, lab, arm, amp, h).exists() for h, _ in K.DIRECTIONS):
                    continue
                stem = stem_of(song, it, lab, arm)
                rb = rebuilt_of(song, it, lab, arm)
                rb32 = rb.astype(np.float32)
                rr.render(rb32, sel, S)                                         # warm-up
                for search, held in K.DIRECTIONS:
                    p = result_path(song, it, lab, arm, amp, search)
                    if p.exists():
                        continue
                    n0 = rr.count
                    curve = []

                    def f(x):
                        v, _ = AM.objective(stem, mono(rr.render(rb32, sel, x)), rb, search)
                        curve.append(v)
                        return v

                    def probe(x):
                        y = mono(rr.render(rb32, sel, x))
                        v, _ = AM.objective(stem, y, rb, search)
                        return AM.peak_dbfs(y), v

                    res = AM.recipe(K.space(amp, S), S, f, probe)
                    j_shrunk = K.judge(rec, mono(rr.render(di32, sel, res["shrunk_x"])), di, LATENCY)
                    j_best = K.judge(rec, mono(rr.render(di32, sel, res["best_x"])), di, LATENCY)
                    _save(p, {"song": song, "item": it, "label": lab, "arm": arm, "amp": amp, "search": search,
                              "held": held, "truth_role": role, "objective_curve": curve, "fallback": res["fallback"],
                              "output": "S" if res["fallback"] else "shrunk", "judge_shrunk": j_shrunk,
                              "judge_best": j_best, "probe": res["probe"], "renders": rr.count - n0 + 1,
                              "settings": {"best": LO.sdict(res["best_x"]), "shrunk": LO.sdict(res["shrunk_x"]),
                                           "output": LO.sdict(res["output_x"])}})
                    print(song, arm, it, lab, amp, search, "held", round(j_shrunk[held], 4), flush=True)
    finally:
        rr.close()
    print(f"SEARCH DONE {args.shard[0]}/{args.shard[1]}")


# --- report ------------------------------------------------------------------------------------------

def unit_log(r, s_judge):
    """log(d_A / d_S) on the held half; S's own distance when the output fell back to S."""
    h = r["held"]
    ds = s_judge[h]
    da = ds if r["output"] == "S" else r["judge_shrunk"][h]
    if not (ds and da and ds > 0 and da > 0 and math.isfinite(ds) and math.isfinite(da)):
        return None
    return math.log(da / ds)


def knob_errors(out_settings, truth_settings, s_settings, dims):
    """{dim: (|θ_out − θ_true|, |θ_S − θ_true|)} on the unit scale, over continuous dimensions."""
    out = {}
    for d in dims:
        if d.kind not in ("cont", "log"):
            continue
        k = d.name
        if k not in truth_settings:
            continue
        t = d.to_unit(truth_settings[k])
        out[k] = (abs(d.to_unit(out_settings.get(k, s_settings.get(k, d.lo))) - t),
                  abs(d.to_unit(s_settings.get(k, d.lo)) - t))
    return out


def cmd_report(_args):
    from learn import knob_ceiling as K

    plan = load_plan()
    tr = _load(OUT / "truth" / "truth.json")
    rows = {}
    knobs = []
    renders = sum(v.get("renders", 0) for v in tr.values())
    for p in sorted((OUT / "results").glob("*/*.json")):
        r = json.loads(p.read_text())
        if p.name.startswith("S-"):
            renders += r["renders"]
            continue
        renders += r["renders"]
        song = r["song"]
        sj = json.loads((p.parent / f"S-{r['label']}-{r['amp']}.json").read_text())
        v = unit_log(r, sj["judge"])
        if v is None:
            continue
        band = SONGS[song]["band"]
        truth = tr[song]["draws"][r["truth_role"]]
        key = (r["item"], r["label"])
        rows.setdefault(r["arm"], []).append({"band": band, "song": song, "item": r["item"], "label": r["label"],
                                              "amp": r["amp"], "search": r["search"], "truth_amp": r["amp"] == truth["amp"], "v": v,
                                              "key": key, "fallback": r["fallback"]})
        if r["amp"] == truth["amp"]:
            dims = K.space(r["amp"])
            ke = knob_errors(r["settings"]["output"], truth["settings"], sj["settings"], dims)
            knobs.append({"band": band, "song": song, "arm": r["arm"], "item": r["item"], "amp": r["amp"], "errors": ke})

    def wt(arm, pred):
        return weighted([(x["band"], x["song"], x["key"], x["v"]) for x in rows.get(arm, []) if pred(x)])

    rep = {"renders": renders, "expected_search_renders": plan.get("expected_renders_search"),
           "A_vs_S": {"primary": wt("A", lambda x: x["item"] in PRIMARY_ITEMS),
                      "primary_truth_amp": wt("A", lambda x: x["item"] in PRIMARY_ITEMS and x["truth_amp"]),
                      "primary_other_amps": wt("A", lambda x: x["item"] in PRIMARY_ITEMS and not x["truth_amp"]),
                      **{f"item_{k}": wt("A", lambda x, k=k: x["item"] == k) for k in ITEMS},
                      "noisy_di": wt("A", lambda x: plan["songs"][x["song"]]["noisy_di"] and x["item"] in PRIMARY_ITEMS),
                      "fresh_song_apprehended": wt("A", lambda x: x["song"] == "apprehended" and x["item"] in PRIMARY_ITEMS),
                      "repeat_use_songs": wt("A", lambda x: x["song"] != "apprehended" and x["item"] in PRIMARY_ITEMS),
                      **{f"song_{sg}": wt("A", lambda x, sg=sg: x["song"] == sg and x["item"] in PRIMARY_ITEMS)
                         for sg in SONGS},
                      "clean_di": wt("A", lambda x: not plan["songs"][x["song"]]["noisy_di"] and x["item"] in PRIMARY_ITEMS)},
           "O_vs_S": wt("O", lambda x: True)}
    # paired contrasts against item 1, per (song, label, amp, search) unit
    a = {(x["song"], x["label"], x["amp"], x["search"], x["item"]): x["v"] for x in rows.get("A", [])}
    o = {(x["song"], x["label"], x["amp"], x["search"]): x["v"] for x in rows.get("O", [])}
    for k in (2, 4, 5):
        pr = [(SONGS[s]["band"], s, lab, v - a[(s, lab, amp, h, 1)]) for (s, lab, amp, h, it), v in a.items()
              if it == k and (s, lab, amp, h, 1) in a]
        rep[f"item_{k}_minus_item_1"] = weighted(pr)
    pr = [(SONGS[s]["band"], s, lab, v - o[(s, lab, amp, h)]) for (s, lab, amp, h, it), v in a.items()
          if it in (1, 3) and (s, lab, amp, h) in o]
    rep["A_minus_O"] = weighted(pr)
    prim = rep["A_vs_S"]["primary"]
    up, n = b2_songs(prim.get("sd"), prim.get("bands", 0))
    rep["b2"] = {"sd_between_bands": prim.get("sd"), "sd_upper_90": up, "songs_for_h_0.03": n}
    ke = {}
    for x in knobs:
        for k, (eo, es) in x["errors"].items():
            ke.setdefault((x["arm"], k), []).append((x["band"], x["song"], x["item"], eo - es))
    rep["knob_error_minus_S"] = {f"{arm}|{k}": weighted(v) for (arm, k), v in ke.items()}
    rep["truth"] = {s: {r: {k: v[k] for k in ("preset", "amp", "class", "draws")} for r, v in tr[s]["draws"].items()}
                    for s in tr}
    rep["checks"] = {s: tr[s].get("checks") for s in tr}
    rep["section_flags"] = {s: plan["songs"][s]["section_flags"] for s in plan["songs"]}
    rep["fallbacks"] = sum(1 for xs in rows.values() for x in xs if x["fallback"])
    rep["mix"] = _load(OUT / "mix" / "log.json")
    _save(OUT / "report.json", rep)
    print(json.dumps({k: rep[k] for k in ("renders", "A_vs_S", "O_vs_S", "A_minus_O", "b2")}, indent=1))
    print("REPORT DONE")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("plan", "truth", "mix", "separate", "rebuild", "report"):
        sub.add_parser(c)
    s = sub.add_parser("search")
    s.add_argument("--shard", type=lambda v: tuple(int(x) for x in v.split("/")), required=True)
    a = ap.parse_args(argv)
    {"plan": cmd_plan, "truth": cmd_truth, "mix": cmd_mix, "separate": cmd_separate, "rebuild": cmd_rebuild,
     "search": cmd_search, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
