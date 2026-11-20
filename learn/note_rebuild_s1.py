"""Stage 1 of the note rebuild, the true-notes test (`docs/note-rebuild-plan.md` section 11; ledger `note-rebuild`
`phase_nr_1`): on the replay's drawn GOAT parts that carry true notes, three dry guitars re-synthesised from GOAT's
true notes (`nr-plain`, `nr-level`, and the diagnostic `nr-oracle`) stand in for the replay's blurred DI, and the
replay's own pick and score read them against Cen and a blind pick on the GOAT-alone row.

    .venv/bin/python -m learn.note_rebuild_s1 subset   # the carrying subset (zero renders), its sha256 -> phase_nr_1_subset
    .venv/bin/python -m learn.note_rebuild_s1 build    # the dry guitars and their figures (CPU, zero renders)
    .venv/bin/python -m learn.note_rebuild_s1 gate     # prints the gate's reading from the replay's report
    .venv/bin/python -m learn.note_rebuild_s1 clips    # the ear check's clips on development items (48 renders)
    .venv/bin/python -m learn.note_rebuild_s1 render --shard k/3     # after the gate and the ear check (phase_nr_1_ear)
    .venv/bin/python -m learn.note_rebuild_s1 pick     # picks.json, its sha256 -> phase_nr_1_picks
    .venv/bin/python -m learn.note_rebuild_s1 score    # the rows, then N1_TABLE's code (once)

`subset` and `build` read no held-half value and render nothing; they may run before the replay's gate. `clips`,
`render`, `pick` and `score` refuse unless the gate reads go (`gate_refusal`, from the replay's own report and main's
ledger), and every command refuses unless this checkout runs main's code and main's ledger holds the phases it needs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import time

from learn import note_rebuild as NR

LEDGER_ID = NR.LEDGER_ID
PHASE_1 = "phase_nr_1"                  # the declaration
PHASE_SUBSET = "phase_nr_1_subset"      # subset.json's sha256: before `build` and any render
PHASE_EAR = "phase_nr_1_ear"            # the user's ear check of the clips: {"verdict": "ok" | "fault", ...}
PHASE_BOTH_GO = "phase_nr_1_both_go"    # the user's go after a Both-row note (only when the replay's outcome has one)
PHASE_PICKS = "phase_nr_1_picks"        # picks.json's sha256: before `score` loads a held-half value
REPLAY_LEDGER = "preset-ladder"
GO_CODES = ("R-alone", "R-dry-only")    # the replay's continue codes; every other code stops stage 1
CLIP_SEED = 20261211                    # the ear check's development items
CLIP_ITEMS = 4
CLIP_AMP = "ac20"
TERTILES = 3
# The carrying subset, hashed at declaration (2026-11-20, before the replay's `pick` or `score`): the replay's draw file
# and the sorted part keys `carrying_subset` gives on stage P's true-notes.json. `subset` refuses any other.
DECLARED_SUBSET = {"draw_sha256": "c0f834ada8d1d42b337be02a5f10812a3888353e6691a943500bf4a4b344f470",
                   "parts": 60, "keys_sha256": "6570fa70ba80f06119c7de08168b98caad732a68fe694650dec26d690387dac9"}
BESIDE_F0 = "without_alignment_f0"      # every row read beside without the parts whose GOAT alignment F is 0.0
CODE_FILES = ("learn/note_rebuild.py", "learn/note_rebuild_s1.py")


def out_dir():
    return NR.OUT / "stage1"


def subset_path():
    return out_dir() / "subset.json"


def build_path():
    return out_dir() / "build.json"


def dry_path(arm, pkey):
    return out_dir() / "di" / arm / f"{pkey.replace('/', '__')}.npy"


def dist_path(arm, pkey):
    return out_dir() / "dist" / arm / f"{pkey.replace('/', '__')}.json"


def picks_path():
    return out_dir() / "picks.json"


def report_path():
    return out_dir() / "report.json"


def rows_path():
    return out_dir() / "report-rows.json"


# --- pure pieces --------------------------------------------------------------------------------------------------------

def carrying_subset(parts, units):
    """(Pure.) The replay's drawn GOAT parts that carry true notes. parts: the draw's; units: true-notes.json's
    {unit|amp: record}. -> (carrying [{pkey, unit, amp, item, window_s}], left out [{pkey, why}])."""
    keep, out = [], []
    for p in sorted((p for p in parts if p["set"] == "goat"), key=lambda p: p["pkey"]):
        r = units.get(f"{p['unit']}|{p['amp']}")
        if r is None:
            out.append({"pkey": p["pkey"], "why": "not in true-notes.json"})
        elif not r.get("carries"):
            out.append({"pkey": p["pkey"], "why": r.get("why", "does not carry")})
        else:
            keep.append({"pkey": p["pkey"], "unit": p["unit"], "amp": p["amp"], "item": r["item"],
                         "window_s": r["window_s"]})
    return keep, out


def gate_refusal(report, replay_main, nr_main):
    """(Pure.) Why stage 1 may not render, or None. report: the replay's report.json (or None); replay_main: main's
    `preset-ladder` entry; nr_main: main's `note-rebuild` entry. The gate reads go only when the replay has been read
    from the hashed picks on main, its outcome is audited and recorded on main (`phase_replay_outcome`), its code is a
    continue code (R-alone or R-dry-only: the dry-guitar row passed, by the combined blur or a single one, and the stem
    alone passed), and, when its outcome carries a Both-row note, the user's go is recorded on main
    (`phase_nr_1_both_go`). The single-blur rows are part of the replay's outcome: a blurred-DI fail or undecided row
    reads `singles-triggered` until they are read, which is not a go."""
    if report is None:
        return "the replay has not been read (no report.json)"
    rec = (replay_main or {}).get("phase_replay_picks")
    if not isinstance(rec, dict) or rec.get("sha256") != report.get("picks_sha256"):
        return "the replay's report was not read from the picks hashed on main"
    if "phase_replay_outcome" not in (replay_main or {}):
        return "the replay's outcome is not audited and recorded on main (phase_replay_outcome)"
    code = (report.get("outcome") or {}).get("code")
    if code not in GO_CODES:
        return f"the replay reads {code}: stage 1 does not run"
    if (report.get("outcome") or {}).get("both_notes") and PHASE_BOTH_GO not in (nr_main or {}):
        return "the replay's outcome carries a Both-row note: the user is asked before stage 1 (phase_nr_1_both_go)"
    return None


def subset_refusal(draw_sha, keys, declared=DECLARED_SUBSET):
    """(Pure.) Why the subset is not the one declared, or None: the replay's draw file and the sorted part keys must
    hash to the declaration's."""
    if draw_sha != declared["draw_sha256"]:
        return "the replay's draw is not the one the subset was declared on"
    if len(keys) != declared["parts"] or NR.content_sha(sorted(keys)) != declared["keys_sha256"]:
        return "the carrying parts are not the declared 60"
    return None


def without_f0(sub_parts):
    """(Pure.) The subset's part keys whose GOAT alignment F is not 0.0 (the beside row)."""
    return [k["pkey"] for k in sub_parts if k.get("alignment_f") != 0.0]


def ear_refusal(nr_main):
    """(Pure.) Why the ear check does not allow stage 1's renders, or None."""
    rec = (nr_main or {}).get(PHASE_EAR)
    if not isinstance(rec, dict) or "verdict" not in rec:
        return "the ear check of the clips is not recorded on main (phase_nr_1_ear)"
    if rec["verdict"] != "ok":
        return f"the ear check reads {rec['verdict']}: fix the fault under a declared revision first"
    return None


def ref_on_section(ref, n, trim, delay):
    """(Pure.) The clean record moved onto the DI section's timeline: the record is trimmed (it starts `trim` samples
    into the section) and lags the DI by `delay` samples (the plugin's latency plus the part's judge lag). -> n
    samples, zeros where the record has none."""
    import numpy as np

    out = np.zeros(n)
    shift = trim - delay                               # section index t holds record index t - shift
    lo, hi = max(0, shift), min(n, shift + len(ref))
    if hi > lo:
        out[lo:hi] = ref[lo - shift:hi - shift]
    return out


def tertile_edges(values, k=TERTILES):
    """(Pure.) The k-1 edges splitting the sorted finite values into k groups of near-equal size."""
    v = sorted(x for x in values if x is not None and math.isfinite(x))
    if len(v) < k:
        return []
    return [v[(len(v) * j) // k] for j in range(1, k)]


def group_of(x, edges):
    """(Pure.) The tertile index of x (0 lowest) by `edges`; None for a missing value."""
    if x is None or not math.isfinite(x):
        return None
    return sum(x >= e for e in edges)


def blind_setting(pkey, menu_n, seed=CLIP_SEED + 1):
    """(Pure.) Stage 3's blind menu setting for a part: a seeded menu position other than Cen (position 0)."""
    return 1 + random.Random(f"{seed}|blind|{pkey}").randrange(menu_n - 1)


def n3_card_eligible(pick, blind):
    """(Pure.) A stage-3 card is drawn only where the pick differs from Cen (position 0) and from the blind setting: an
    equal pair is a forced tie, which the sign test leaves out anyway; such parts are counted and reported."""
    return pick is not None and pick != 0 and pick != blind


# --- main's ledger and code -----------------------------------------------------------------------------------------------

def _git(*a):
    import subprocess

    return subprocess.run(["git", "-C", str(NR.REPO), *a], capture_output=True, text=True)


def main_entries():
    """(main's `note-rebuild` entry, main's `preset-ladder` entry, refusal or None): after a fetch, the code files must
    equal main's and this checkout's `note-rebuild` phase keys main's."""
    _git("fetch", "-q", "origin", "main")
    led = _git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        return None, None, f"main's ledger is not readable: {led.stderr.strip()}"
    d = json.loads(led.stdout)
    nr = next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), None)
    rp = next((t for t in d["tests"] if t["test_id"] == REPLAY_LEDGER), None)
    for f in CODE_FILES:
        if _git("diff", "--quiet", "origin/main", "--", f).returncode:
            return nr, rp, f"this checkout's {f} differs from main's: run from merged code"
    local = NR.ledger_entry() or {}
    a = {k: v for k, v in local.items() if k.startswith("phase_nr")}
    b = {k: v for k, v in (nr or {}).items() if k.startswith("phase_nr")}
    if a != b:
        return nr, rp, "this checkout's phase_nr keys differ from main's: pull main"
    return nr, rp, None


def require(*phases):
    """Refuse unless this checkout's `note-rebuild` entry holds every phase."""
    for k in phases:
        NR.require(k)


def require_main(*phases):
    nr, rp, why = main_entries()
    if why:
        raise SystemExit(why)
    for k in phases:
        if k not in (nr or {}):
            raise SystemExit(f"main's {LEDGER_ID} entry has no {k}: merge it before running")
    return nr, rp


def require_file_hash(nr, phase, path):
    rec = (nr or {}).get(phase)
    sha = NR.file_sha(path)
    if not isinstance(rec, dict) or rec.get("sha256") != sha:
        raise SystemExit(f"{path.name}'s sha256 {sha[:12]} is not main's {phase}")
    return json.loads(pathlib.Path(path).read_text())


def require_gate(nr, rp):
    from learn import note_replay as R

    rpth = R.report_path()
    why = gate_refusal(json.loads(rpth.read_text()) if rpth.exists() else None, rp, nr)
    if why:
        raise SystemExit(f"the gate is closed: {why}")


# --- the commands ----------------------------------------------------------------------------------------------------------

def cmd_subset(_args):
    """The carrying subset (zero renders, no held-half value): the replay's drawn GOAT parts that carry true notes, from
    the replay's hashed draw and stage P's true-notes.json. -> stage1/subset.json; its sha256 goes into the ledger as
    phase_nr_1_subset before `build` or any render."""
    require(PHASE_1)
    require_main(PHASE_1)
    NR.refuse_existing(subset_path())
    from learn import note_replay as R              # after the refusals

    draw = R.require_draw()
    tn = NR.load_doc("true-notes.json")
    keep, out = carrying_subset(draw["parts"], tn["units"])
    why = subset_refusal(R.file_sha(R.draw_path()), [k["pkey"] for k in keep])
    if why:
        raise SystemExit(why)
    for k in keep:
        rec = tn["items"][k["item"]]
        k["notes_sha256"] = rec["notes_sha256"]
        k["notes_file_sha256"] = NR.file_sha(NR.OUT / "true-notes" / f"{k['item']}.json")
        u = tn["units"][f"{k['unit']}|{k['amp']}"]
        for f in ("cls", "fold", "alignment_f", "guitar", "tuning", "player", "tab_share", "articulated", "notes"):
            k[f] = u.get(f)
    doc = {"plan": NR.PLAN, "ledger": f"{LEDGER_ID} {PHASE_1}", "draw_sha256": R.file_sha(R.draw_path()),
           "true_notes_body_sha256": NR.content_sha(tn), "parts": keep, "left_out": out,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    NR.write_once(subset_path(), doc)
    print(f"SUBSET: {len(keep)} carrying, {len(out)} left out; sha256 {NR.file_sha(subset_path())} "
          f"(into the ledger as {PHASE_SUBSET} before anything else)")


def require_subset(nr):
    from learn import note_replay as R

    sub = require_file_hash(nr, PHASE_SUBSET, subset_path())
    if sub["draw_sha256"] != R.file_sha(R.draw_path()):
        raise SystemExit("subset.json was made from another draw")
    return sub


def load_item_notes(k):
    """One subset part's notes, refused unless the file is the one hashed into the subset."""
    p = NR.OUT / "true-notes" / f"{k['item']}.json"
    if NR.file_sha(p) != k["notes_file_sha256"]:
        raise SystemExit(f"{p.name}: not the note file the subset hashed")
    rec = json.loads(p.read_text())
    if NR.content_sha(rec["notes"]) != k["notes_sha256"]:
        raise SystemExit(f"{p.name}: its notes are not the subset's")
    return rec["notes"]


def cmd_build(_args):
    """The dry guitars (CPU, zero renders, no held-half value): per subset part, the true DI section as the replay
    renders it (`note_replay.di_section`), the window's true notes moved by the oracle onset step against it, the clean
    record on the section's timeline (`ref_on_section`), and the three arms through `note_rebuild.rebuild_dry` with the
    blurred row's chain as `finish` (`song_bank.measure`, then `di_robustness.average_balance` with the part's
    `others`, the replay's `others_for`); every arm at -22.9 LUFS. The figures against the true DI as rendered beside.
    -> stage1/di/<arm>/<part>.npy, stage1/build.json."""
    require(PHASE_1, PHASE_SUBSET)
    nr, _ = require_main(PHASE_1, PHASE_SUBSET)
    NR.refuse_existing(build_path())
    sub = require_subset(nr)
    import numpy as np                              # after the refusals

    from learn import di_robustness as DR
    from learn import knob_ceiling as K
    from learn import note_replay as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    draw = R.require_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    bank = NR.Bank(NR.load_notes_doc())
    by = {p["pkey"]: p for p in draw["parts"]}
    by_sec = {}
    for p in draw["parts"]:
        by_sec.setdefault(p["section"], sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    cache = {}

    def sec(s):
        if s not in cache:
            cache[s] = np.asarray(R.di_section(by_sec[s]), np.float64)
        return cache[s]
    trim = int(PS.TRIM_S * PS.SR)
    out, t0 = {"plan": NR.PLAN, "subset_sha256": NR.file_sha(subset_path()), "parts": {}}, time.time()
    for n_, k in enumerate(sub["parts"]):
        p = by[k["pkey"]]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di = sec(p["section"])
        n = len(di)
        notes = NR.window_notes(load_item_notes(k), k["window_s"] - PS.TRIM_S, n / PS.SR)
        offset = NR.coarse_offset(notes, di)
        refined, shifts = NR.refine_onsets(NR.shifted_notes(notes, offset), di)
        clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        ref = ref_on_section(np.asarray(clean, np.float64), n, trim, K.P.LATENCY + p["lag"])
        others = {s: [sec(x) for x in xs] for s, xs in R.others_for(p, draw["parts"]).items()}

        def finish(y, others=others):
            return DR.average_balance(SB.measure(y), others)
        rec = {"notes": len(notes), "window_offset_ms": 1000 * offset,
               "onset_shift_ms": {"median": 1000 * float(np.median(np.abs(shifts))) if shifts
                                                       else None, "moved": sum(s != 0 for s in shifts),
                                                       "groups": len(shifts)},
               "arms": {}}
        for arm in NR.ARMS:
            y, rep = NR.rebuild_dry(arm, refined, n, bank, ref, di=di, finish=finish)
            y32 = np.asarray(y, np.float32)
            if len(y32) != n or not np.isfinite(y32).all():
                raise SystemExit(f"{k['pkey']}: a bad {arm} dry guitar")
            path = dry_path(arm, k["pkey"])
            NR.refuse_existing(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, y32)
            rec["arms"][arm] = {"sha256": NR.file_sha(path), "report": rep, "figures": NR.figures(di, y)}
        out["parts"][k["pkey"]] = rec
        if n_ % 10 == 0:
            print(f"build {n_ + 1}/{len(sub['parts'])}: {(time.time() - t0) / (n_ + 1):.1f} s each", flush=True)
    NR.write_once(build_path(), out)
    print(f"BUILD DONE: {len(out['parts'])} parts x {len(NR.ARMS)} arms, {time.time() - t0:.0f} s; "
          f"sha256 {NR.file_sha(build_path())}")


def load_arm(arm, pkey, build):
    import numpy as np

    path = dry_path(arm, pkey)
    if NR.file_sha(path) != build["parts"][pkey]["arms"][arm]["sha256"]:
        raise SystemExit(f"{path.name}: not the dry guitar `build` wrote")
    return np.load(path).astype(np.float32)


def cmd_gate(_args):
    """Prints the gate's reading (refuses nothing; reads main's ledger and the replay's report)."""
    from learn import note_replay as R

    nr, rp, why = main_entries()
    rpth = R.report_path()
    g = gate_refusal(json.loads(rpth.read_text()) if rpth.exists() else None, rp, nr)
    print(json.dumps({"code_on_main": why is None, "why_not": why, "gate": "go" if g is None else g,
                      "ear": ear_refusal(nr) or "ok"}, indent=1))


def clip_items(meta_items, excl, used, seed=CLIP_SEED, k=CLIP_ITEMS):
    """(Pure but for `clear_of`.) The ear check's development items: GOAT items with fine-aligned MIDI, clear of the
    exclusion list and not among `used`, a seeded sample of k."""
    pool = sorted(it for it in meta_items if not NR.clear_of({"goat_item": it}, excl) and it not in used)
    return sorted(random.Random(f"{seed}|clips").sample(pool, min(k, len(pool))))


def cmd_clips(_args):
    """The ear check before stage 1 (the plan review's item 3): CLIP_ITEMS development GOAT items clear of the
    exclusion list (seeded), a 10-s window each; the true DI (through `song_bank.measure`), `nr-plain` and `nr-level`
    (finished by `song_bank.measure`), each through the clean and crunch class starts S on CLIP_AMP, each render primed
    alone: 4 x 3 x 2 = 24 kept, 48 renders. Guitar only, the dry guitar switchable per preset. After the gate.
    -> ~/ndsp-presets/listening/note-rebuild-ear/<item>-<dry>-<cls>.wav, index.json. The user's verdict goes into the
    ledger as phase_nr_1_ear ("ok", or "fault" with what was heard)."""
    require(PHASE_1, PHASE_SUBSET)
    nr, rp = require_main(PHASE_1, PHASE_SUBSET)
    require_gate(nr, rp)
    dest = NR.HOME / "listening" / "note-rebuild-ear"
    NR.refuse_existing(dest)
    import csv                                      # after the refusals
    import io
    import zipfile

    import numpy as np
    import soundfile as sf

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import clean_di as CD
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    excl = NR.load_exclusion()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    ms = P.A_menu_S()[CLIP_AMP]
    sec = int(round((PS.SEC_S + PS.TRIM_S) * PS.SR))
    trim = (int(PS.TRIM_S * PS.SR), sec)
    LO._wait_cap()
    index = {"plan": NR.PLAN, "amp": CLIP_AMP, "clips": []}
    with zipfile.ZipFile(NR.GOAT_ZIP) as z:
        names = set(z.namelist())
        meta = {r["item"]: r for r in csv.DictReader(io.StringIO(z.read("GOAT/metadata.csv").decode()))}
        items = clip_items([it for it in meta if f"GOAT/data/{it}/{it}_fine_aligned.mid" in names], excl, set())
        NR.assert_clear([{"goat_item": it} for it in items], excl)
        dest.mkdir(parents=True)
        for it in items:
            rec = NR.true_notes_for(it, z, meta)
            x, sr = sf.read(io.BytesIO(z.read(f"GOAT/data/{it}/{it}.wav")), dtype="float64", always_2d=True)
            x = CD.resample(x.mean(1), sr, PS.SR)
            start = 30.0 if len(x) / PS.SR > 45 else 1.0
            di = SB.measure(x[int(start * PS.SR):int(start * PS.SR) + sec])
            wn = NR.window_notes(rec["notes"], start, sec / PS.SR)
            notes, _ = NR.refine_onsets(NR.shifted_notes(wn, NR.coarse_offset(wn, di)), di)
            drys = {"true": di}
            for arm in ("nr-plain", "nr-level"):
                drys[arm], _ = NR.rebuild_dry(arm, notes, sec, bank, di, finish=SB.measure)
            for cls in ("clean", "crunch"):
                sel, S = ms[cls]
                s_ = LO.tdict(LO.sdict(dict(S)))
                for dname, y in drys.items():
                    out = np.asarray(AM.fresh_render(CB.new_renderer, np.asarray(y, np.float32), sel, s_, s_),
                                     np.float64)[trim[0]:trim[1]]
                    f = dest / f"{it}-{dname}-{cls}.wav"
                    sf.write(f, (out / (np.abs(out).max() + 1e-9) * 0.5).astype(np.float32), PS.SR)
                    index["clips"].append({"item": it, "dry": dname, "cls": cls, "file": f.name,
                                           "sha256": NR.file_sha(f)})
    NR.write_once(dest / "index.json", index)
    print(f"CLIPS DONE: {len(index['clips'])} clips in {dest}")


def cmd_render(args):
    """One shard's renders (after the gate and the ear check): each subset part's three arms through its 23 menu
    settings in the replay's position-check mode (`note_replay.render_menu`), each kept render's search-half distance
    against the clean record (`note_replay.half_distance`, the dry guitar as the judge's DI), no held-half distance, no
    audio kept. -> stage1/dist/<arm>/<part>.json."""
    require(PHASE_1, PHASE_SUBSET, PHASE_EAR)
    nr, rp = require_main(PHASE_1, PHASE_SUBSET, PHASE_EAR)
    require_gate(nr, rp)
    why = ear_refusal(nr)
    if why:
        raise SystemExit(why)
    sub = require_subset(nr)
    if not build_path().exists():
        raise SystemExit("run `build` first")
    build = json.loads(build_path().read_text())
    if build["subset_sha256"] != NR.file_sha(subset_path()):
        raise SystemExit("build.json was made from another subset")
    from learn import note_replay as R              # after the refusals

    pos = R.control_path("position")
    if not pos.exists():
        raise SystemExit("the replay's position check is missing")
    mode = json.loads(pos.read_text())["mode"]
    R.no_separation_beside()
    import numpy as np

    from learn import audibility_measure as AM
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    draw = R.require_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    by = {p["pkey"]: p for p in draw["parts"]}
    k_, n_ = args.shard
    mine = [k for j, k in enumerate(sorted(x["pkey"] for x in sub["parts"])) if j % n_ == k_]
    LO._wait_cap()
    renders, t0 = 0, time.time()
    for key in mine:
        p = by[key]
        todo = [a for a in NR.ARMS if not dist_path(a, key).exists()]
        if not todo:
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        _, clean, trim = R.part_audio(sd, p)
        for arm in todo:
            t1 = time.time()
            x32 = load_arm(arm, key, build)
            dj = np.asarray(x32, np.float64)[trim[0]:trim[1]]
            ys, used = R.render_menu(x32, p["menu"], mode)
            renders += used
            rec = {"plan": NR.PLAN, "part": key, "arm": arm, "mode": mode, "lag": p["lag"], "search": p["search"],
                   "menu_sha256": hashlib.sha256(json.dumps(p["menu"], sort_keys=True).encode()).hexdigest(),
                   "distances": [R.half_distance(clean, y, dj, p["lag"], p["search"]) for y in ys],
                   "render_sha256": [AM.audio_sha(y) for y in ys], "renders": used, "seconds": time.time() - t1}
            path = dist_path(arm, key)
            NR.write_once(path, rec)
        print(f"{key[-60:]}: renders so far {renders}, {time.time() - t0:.0f} s", flush=True)
    print(f"NR1-RENDER DONE {k_}/{n_}: {renders} renders in {time.time() - t0:.0f} s")


def load_dist(arm, p):
    path = dist_path(arm, p["pkey"])
    if not path.exists():
        return None
    rec = json.loads(path.read_text())
    if rec["menu_sha256"] != hashlib.sha256(json.dumps(p["menu"], sort_keys=True).encode()).hexdigest():
        raise SystemExit(f"{path.name}: rendered from another menu")
    return rec


def cmd_pick(_args):
    """The picks (zero renders; distances only): per arm and subset part the menu position with the smallest
    search-half distance (`note_replay.pick_index`). -> stage1/picks.json; its sha256 goes into the ledger as
    phase_nr_1_picks before `score`."""
    require(PHASE_1, PHASE_SUBSET, PHASE_EAR)
    nr, rp = require_main(PHASE_1, PHASE_SUBSET, PHASE_EAR)
    require_gate(nr, rp)
    sub = require_subset(nr)
    NR.refuse_existing(picks_path())
    from learn import note_replay as R

    draw = R.require_draw()
    by = {p["pkey"]: p for p in draw["parts"]}
    out = {"plan": NR.PLAN, "subset_sha256": NR.file_sha(subset_path()), "rows": {}, "dist_sha256": {},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    for arm in NR.ARMS:
        out["rows"][arm] = {}
        for k in sub["parts"]:
            rec = load_dist(arm, by[k["pkey"]])
            if rec is None:
                raise SystemExit(f"{k['pkey']}: no {arm} renders")
            out["dist_sha256"][f"{arm}/{k['pkey']}"] = NR.file_sha(dist_path(arm, k["pkey"]))
            out["rows"][arm][k["pkey"]] = {"pick": R.pick_index(rec["distances"]),
                                           "pick_nl": R.pick_index(rec["distances"], skip=(R.LABEL_INDEX,))}
    NR.write_once(picks_path(), out)
    print(f"NR1-PICKS: {len(sub['parts'])} parts x {len(NR.ARMS)} arms; sha256 {NR.file_sha(picks_path())} "
          f"(into the ledger as {PHASE_PICKS} before `score`)")


def breakdowns(sub_parts, per, band_rows):
    """The arm's breakdowns at no render cost: by alignment-F tertile, Strat or not, tab-matched share at 0.8 or more,
    articulated share at or below the subset's median, clean or crunch. per: {pkey: part numbers}; band_rows: a
    function (parts, values) -> the GOAT row. -> {name: {group: {G, I}}}."""
    import statistics

    edges = tertile_edges([k["alignment_f"] for k in sub_parts])
    arts = [k["articulated"] for k in sub_parts if k["articulated"] is not None]
    med = statistics.median(arts) if arts else None
    splits = {
        "alignment_f_tertile": lambda k: group_of(k["alignment_f"], edges),
        "strat": lambda k: k["guitar"] == "strat",
        "tab_share_0.8": lambda k: (k["tab_share"] or 0) >= NR.CARRY_TAB_SHARE,
        "articulated_low": lambda k: None if med is None or k["articulated"] is None else k["articulated"] <= med,
        "cls": lambda k: k["cls"]}
    out = {"alignment_f_edges": edges, "articulated_median": med}
    for name, f in splits.items():
        groups = {}
        for k in sub_parts:
            groups.setdefault(str(f(k)), []).append(k["pkey"])
        out[name] = {g: {q: band_rows(ks, {k: (per.get(k) or {}).get(q) for k in ks}) for q in ("G", "I")}
                     for g, ks in sorted(groups.items())}
    return out


def cmd_score(_args):
    """The read (zero renders), once: refused unless picks.json's sha256 is main's phase_nr_1_picks. Per arm: each
    part's numbers (`note_replay.part_numbers` on the stored held-half scores), the GOAT row of G and I
    (`note_replay.summary`'s `goat`: GOAT items as clusters), its reading (`note_rebuild.row_reading`), beside the
    replay's GOAT-alone Control, Blurred and blind rows recomputed on exactly the subset from the replay's own
    distance files, each arm's share of the Blurred row's I, the breakdowns, the label-free numbers and the
    spearman with the true DI's distances. The rows are saved before N1_TABLE's code is read.
    -> stage1/report-rows.json, then stage1/report.json."""
    require(PHASE_1, PHASE_SUBSET, PHASE_EAR, PHASE_PICKS)
    nr, rp = require_main(PHASE_1, PHASE_SUBSET, PHASE_EAR, PHASE_PICKS)
    require_gate(nr, rp)
    sub = require_subset(nr)
    picks = require_file_hash(nr, PHASE_PICKS, picks_path())
    NR.refuse_existing(report_path())
    NR.refuse_existing(rows_path())
    NR.table_guard()
    from learn import note_replay as R

    draw = R.require_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    by = {p["pkey"]: p for p in draw["parts"]}
    parts = [by[k["pkey"]] for k in sub["parts"]]
    band = R.lender_band()

    def goat_row(keys, values):
        ps = [by[k] for k in keys]
        return R.summary(sd.units, ps, values, band)["goat"]
    hs = {p["pkey"]: R.h_of(sd.held((p["set"], p["unit"], p["amp"]), p["menu"])) for p in parts}
    true_d = {p["pkey"]: R.load_dist("true", p)["distances"]["clean"] for p in parts}
    rows = {}
    nof0 = without_f0(sub["parts"])
    for name, dry in (("control", "true"), ("blurred", "avg+mild")):     # the replay's, on exactly the subset
        per = {p["pkey"]: R.part_numbers(R.load_dist(dry, p)["distances"]["clean"], hs[p["pkey"]]) for p in parts}
        rows[name] = {"parts": per, **{q: goat_row([p["pkey"] for p in parts], {k: (v or {}).get(q)
                                                                                for k, v in per.items()})
                                       for q in ("G", "I", "blind")},
                      BESIDE_F0: {q: goat_row(nof0, {k: (per.get(k) or {}).get(q) for k in nof0}) for q in ("G", "I")}}
    for arm in NR.ARMS:
        per = {}
        for p in parts:
            d = load_dist(arm, p)["distances"]
            num = R.part_numbers(d, hs[p["pkey"]])
            if num is not None and (num["pick"] != picks["rows"][arm][p["pkey"]]["pick"]
                                    or num["pick_nl"] != picks["rows"][arm][p["pkey"]]["pick_nl"]):
                raise SystemExit(f"{arm} {p['pkey']}: the distances' pick is not the hashed pick")
            if num is not None:
                num["spearman_vs_true"] = R.spearman(d, true_d[p["pkey"]])
                num["refused_windows"] = sum(not math.isfinite(x) for x in d)
            per[p["pkey"]] = num
        keys = [p["pkey"] for p in parts]
        rows[arm] = {"parts": per, **{q: goat_row(keys, {k: (v or {}).get(q) for k, v in per.items()})
                                      for q in ("G", "I", "G_nl", "I_nl")},
                     "breakdowns": breakdowns(sub["parts"], per, goat_row),
                     BESIDE_F0: {q: goat_row(nof0, {k: (per.get(k) or {}).get(q) for k in nof0}) for q in ("G", "I")},
                     "no_pick": sorted(k for k, v in per.items() if v is None)}
    out = {"plan": NR.PLAN, "ledger": f"{LEDGER_ID} {PHASE_1}", "subset_sha256": NR.file_sha(subset_path()),
           "picks_sha256": NR.file_sha(picks_path()), "time": time.strftime("%Y-%m-%d %H:%M:%S"), "rows": rows}
    NR.write_once(rows_path(), out)                    # the rows are saved before the code is read
    readings = {arm: NR.row_reading(rows[arm]["G"], rows[arm]["I"]) for arm in NR.ARMS}
    bl = rows["blurred"]["I"].get("mean")
    shares = {arm: (rows[arm]["I"].get("mean") / bl if bl else None) for arm in NR.ARMS}
    code = NR.n1_code(readings["nr-plain"], readings["nr-level"])
    final = {**out, "readings": readings, "share_of_blurred_I": shares, "code": code,
             "next": dict((c, t) for c, _, t in NR.N1_TABLE)[code], "arm": NR.n1_arm(readings["nr-plain"],
                                                                                   readings["nr-level"])}
    NR.write_once(report_path(), final)
    for arm in NR.ARMS:
        g, i = rows[arm]["G"], rows[arm]["I"]
        print(f"{arm}: G {g.get('mean')} [{g.get('lo90')}, {g.get('hi90')}], I {i.get('mean')} [{i.get('lo90')}, "
              f"{i.get('hi90')}] -> {readings[arm]}{' (diagnostic)' if arm == 'nr-oracle' else ''}")
    print(f"N1 {code}: {final['next']}")


def _shard(s):
    k, n = (int(x) for x in s.split("/"))
    if not 0 <= k < n or n > 3:
        raise argparse.ArgumentTypeError("k/n with 0 <= k < n <= 3 (at most 3 render processes)")
    return k, n


COMMANDS = {"subset": cmd_subset, "build": cmd_build, "gate": cmd_gate, "clips": cmd_clips, "render": cmd_render,
            "pick": cmd_pick, "score": cmd_score}


def main(argv=None):
    import sys

    for p_ in (str(NR.REPO), str(NR.REPO / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=_shard, default=(0, 1))
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
