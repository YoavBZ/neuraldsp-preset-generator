"""The floors of the sound-gap test (`docs/scratch-voice-plan.md`, phase 3; ledger `preset-ladder`
`phase_scratch_voice`): Unit C. Row (b)'s stored, hashed answer (`answers-fs-stem.json`) rendered through each
rendered guitar (`scratch_voice.RENDERED`: `vc-fin`, `vc-cut`, `vc-own`, `vc-env`, `avg+mild`), each in a fresh primed
process (one discarded priming render, then the kept one: 2 renders), judged by `note_replay.half_distance` on the
held half against the clean record with the true DI as the judge's DI at the part's lag, as
`rederive_rows.cmd_floor_real` does. The true DI's and `tr-di`'s floors are stored (the exact-notes test's
`floors.json`, hashed in `phase_scratch_exact_targets`) and are not rendered again, except in the repeat check.
5 x 47 x 2 = 470 renders, plus 8 for the repeat check.

    $MAIN -m learn.voice_floors floor --shard 0/3           # and 1/3, 2/3: one render process each
    $MAIN -m learn.voice_floors floor --shard 0/3 --rerun   # S1: the refused guitars, once more

**Guards first.** Every command refuses before any render (and before numpy is imported) unless this checkout runs
main's code and keys and main holds the draw, row (b)'s answers, the exact-notes floors, the declaration and
`phase_scratch_voice_dry` (`scratch_voice.require_voice`); build.json's sha256 is main's `phase_scratch_voice_dry` and
its proofs held; the stored floors' and the answers' sha256 are main's; the build and the stored floors cover the
draw's parts. Each guitar is loaded by sha256: its file's (`file_sha256`) and its samples' (`audio_sha256`, the float32
`.npy` form) must be build.json's.

**The repeat check, before the shards' main work.** Shard 0 re-renders `tr-di` and the true DI at row (b)'s answer on
the two check parts (`scratch_voice.check_parts`: the first BKS and the first GOAT part by key): 8 renders. Each held
distance and render sha256 must equal the stored floor's. The result is written once to `repeat/<part>.json`; any
mismatch stops everything. Shards 1 and 2 wait (before they take a render slot) until both records exist, and stop at
once if any does not hold, or after `REPEAT_WAIT_S`.

**The carry.** A guitar byte-identical (`audio_sha256`) to one already floored for the part (the stored true DI or
`tr-di`, or an earlier guitar of `RENDERED`) takes that floor without a render, and the record names it
(`carried_from`).

**S1.** A refusal is a render that is not finite, or a held distance that is not finite and positive (with the true DI
as the judge's DI, only a silent render can refuse). A part with any refused guitar is first written to
`floors-first/<part>.json`, never to `floors/`; `--rerun` reruns only those guitars, once, in its own fresh process,
and writes the part's one `floors/<part>.json` (the passing guitars taken from the first pass byte for byte, the rerun
ones `reran: true`, still refused with their reason if they refuse again). So the read never sees a record with a
pending rerun. Reasons are fixed strings (`REASONS`) with no part key or path: the read copies them into report.json.

**Records** are written once (`write_once`: an exclusive link, never a replace). They and the logs carry 12-hex tags
(`scratch_voice.tag`), never part keys; the files sit under `PF/fs/voice/` (`floors/`, `floors-first/`, `repeat/`).
Disk is checked before each part (`disk_refusal`: stop if free space would fall under 31 GB). At most 3 render
processes in all, one per shard (a render slot each, `local_objective._wait_cap`); every renderer removes its temp
folder on close (`knob_ceiling.Renderer.close`).

The command's body (`run_floor`) runs on a world object (`RealWorld`, or a fake in tests/test_voice_floors.py on the
light CI runner: no numpy, no renders).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import time

from learn import scratch_exact as SE
from learn import scratch_search as S
from learn import scratch_voice as V

PLAN = V.PLAN
MODULE = "learn/voice_floors.py"
SHARDS = 3                               # one render process a shard; at most 3 in all
REPEAT_SHARD = 0                         # the shard that runs the repeat check before its main work
REPEAT_WAIT_S = 1800                     # the other shards wait this long for the repeat records, then stop
REPEAT_POLL_S = 15
RENDERS_EACH = 2                         # a priming render and the kept one
ORDER = V.RENDERED                       # vc-fin, vc-cut, vc-own, vc-env, avg+mild: the render (and carry) order
STORED = V.STORED                        # true, tr-di: stored floors, carry sources, the repeat check's guitars
DISK_GUARD_GB = 31.0                     # trusted_data.DISK_GUARD_GB
PART_DISK_GB = 0.1                       # a part's own writes (its JSON records, a renderer's temp folder) at most
REASONS = {                              # S1's reasons: fixed strings, never a part key or a path
    "nonfinite_render": "the render is not finite",
    "no_distance": "the judge gave no distance (a silent render)",
    "nonfinite_distance": "the held distance is not finite",
    "nonpositive_distance": "the held distance is not positive",
}
FIELDS = ("held", "audio_sha256", "dry_sha256", "refused", "reran", "carried_from")   # a guitar's floor record


# --- the pure parts ---------------------------------------------------------------------------------------------------

def shard_refusal(shard):
    """(Pure.) Why a shard may not run, or None: k/3 with 0 <= k < 3."""
    try:
        k, n = shard
    except (TypeError, ValueError):
        return f"shard {shard!r}: k/{SHARDS}"
    if n != SHARDS or not 0 <= k < n:
        return f"shard {k}/{n}: the floors run as k/{SHARDS}, one render process a shard (at most {SHARDS})"
    return None


def mine(parts, shard):
    """(Pure.) A shard's parts: every n-th of the draw's parts sorted by key (`scratch_exact.mine`)."""
    return SE.mine({"parts": parts}, shard)


def refusal_of(finite_render, held):
    """(Pure.) S1's reason a render refuses, or None: the render not finite; no distance (the judge's refusal reads
    inf); a held distance not finite or not positive."""
    if not finite_render:
        return REASONS["nonfinite_render"]
    if not isinstance(held, (int, float)) or isinstance(held, bool):
        return REASONS["nonfinite_distance"]
    if held == math.inf:
        return REASONS["no_distance"]
    if not math.isfinite(held):
        return REASONS["nonfinite_distance"]
    if held <= 0:
        return REASONS["nonpositive_distance"]
    return None


def disk_refusal(free_gb, need_gb=PART_DISK_GB, guard=DISK_GUARD_GB):
    """(Pure.) Why a part may not start, or None: free space would fall under the guard."""
    if free_gb - need_gb < guard:
        return f"DISK GUARD: {free_gb:.1f} GB free; a part would leave under {guard:.0f} GB"
    return None


def render_floor(held, audio_sha, finite_render, dry_sha, reran=False):
    """(Pure.) One guitar's floor record from its render: held (None unless finite), the render's sha256, the dry
    guitar's sha256, the refusal's reason or None."""
    why = refusal_of(finite_render, held)
    ok = isinstance(held, (int, float)) and not isinstance(held, bool) and math.isfinite(held)
    return {"held": float(held) if ok else None, "audio_sha256": audio_sha, "dry_sha256": dry_sha, "refused": why,
            "reran": reran, "carried_from": None}


def carry_source(sha, settled):
    """(Pure.) The first guitar already floored for the part whose dry guitar is byte-identical (`sha`), or None.
    settled: [(guitar, dry sha256)] in order (the stored true DI and tr-di first, then RENDERED's order)."""
    for g, s in settled:
        if sha and s == sha:
            return g
    return None


def carried(src_rec, dry_sha, src, reran=False):
    """(Pure.) A carried floor: the source's held, render sha256 and refusal, this guitar's own dry sha256."""
    return {"held": src_rec.get("held"), "audio_sha256": src_rec.get("audio_sha256"), "dry_sha256": dry_sha,
            "refused": src_rec.get("refused"), "reran": reran, "carried_from": src}


def floor_guitars(todo, dry_shas, render, stored, done=None, reran=False):
    """(Pure but for `render`.) The floors of one part's guitars `todo`, in order. dry_shas: {guitar: its dry sha256}
    (the rendered guitars' and the stored true DI's and tr-di's); render(guitar) -> (held, render sha256, finite);
    stored: {true, tr-di: {held, audio_sha256}}, the stored floors; done: {guitar: record} already settled for the part
    (the first pass's passing guitars on a rerun). A guitar byte-identical to one already floored takes its floor
    (`carry_source`). -> ({guitar: record}, renders)."""
    out, renders = dict(done or {}), 0
    settled = [(g, dry_shas.get(g)) for g in STORED] + [(g, dry_shas.get(g)) for g in ORDER if g in out]
    floored = {g: {"held": stored[g].get("held"), "audio_sha256": stored[g].get("audio_sha256"),
                   "refused": refusal_of(True, stored[g].get("held"))} for g in STORED}
    for g in todo:
        sha = dry_shas.get(g)
        if not sha:
            raise SystemExit(f"{g}: no declared dry sha256")
        src = carry_source(sha, settled)
        if src is not None:
            out[g] = carried(floored[src] if src in floored else out[src], sha, src, reran)
        else:
            held, audio_sha, finite = render(g)
            renders += RENDERS_EACH
            out[g] = render_floor(held, audio_sha, finite, sha, reran)
        settled.append((g, sha))
    return {g: out[g] for g in ORDER if g in out}, renders


def refused_guitars(rec):
    """(Pure.) A floor record's refused guitars, in RENDERED's order."""
    gs = (rec or {}).get("guitars") or {}
    return [g for g in ORDER if (gs.get(g) or {}).get("refused")]


def repeat_verdict(got, stored):
    """(Pure.) The repeat check on one part: each of the true DI and tr-di's held distance and render sha256 equal to
    the stored floor's. got, stored: {guitar: {held, audio_sha256}}. -> {guitars: {...}, holds}."""
    gs = {}
    for g in STORED:
        a, b = got.get(g) or {}, stored.get(g) or {}
        same_d = a.get("held") is not None and a.get("held") == b.get("held")
        same_sha = bool(a.get("audio_sha256")) and a.get("audio_sha256") == b.get("audio_sha256")
        gs[g] = {"held": a.get("held"), "audio_sha256": a.get("audio_sha256"), "stored_held": b.get("held"),
                 "stored_audio_sha256": b.get("audio_sha256"), "distance_repeats": same_d, "sha_repeats": same_sha,
                 "holds": same_d and same_sha}
    return {"guitars": gs, "holds": all(r["holds"] for r in gs.values()) and len(gs) == len(STORED)}


def repeat_state(recs):
    """(Pure.) The repeat check's state from its records ({pkey: record or None}): "holds" when every check part's
    record holds, "fails" when any existing record does not, else "pending"."""
    if any(r is not None and r.get("holds") is not True for r in recs.values()):
        return "fails"
    if recs and all(r is not None for r in recs.values()) and len(recs) == V.CHECK_PARTS:
        return "holds"
    return "pending"


def first_path(pk):
    """A part's first-pass record when any guitar refused (S1: `--rerun` writes the part's one floors/ record)."""
    return V.voice_dir() / "floors-first" / f"{SE._f(pk)}.json"


def write_once(path, obj, label="a record"):
    """Write JSON once: to a temp file, then an exclusive hard link (refuses if the file exists). No NaN or inf.
    label: what the refusal names (a 12-hex tag, never a part key or path)."""
    path = pathlib.Path(path)
    if path.exists():
        raise SystemExit(f"{label} ({path.parent.name}/): exists, never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1, allow_nan=False) + "\n")
    try:
        os.link(tmp, path)
    except FileExistsError:
        raise SystemExit(f"{label} ({path.parent.name}/): exists, never overwritten") from None
    finally:
        tmp.unlink(missing_ok=True)


def _read(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


# --- the command body (on a world: RealWorld, or a fake in the tests) -------------------------------------------------

def run_repeat(w):
    """The repeat check on the two check parts (8 renders), each record written once; any mismatch stops. A part whose
    record exists is not rendered again (a failed one stops at once)."""
    renders = 0
    for pk in w.check_keys:
        rp = V.repeat_path(pk)
        old = _read(rp)
        if old is not None:
            if old.get("holds") is not True:
                raise SystemExit(f"REPEAT MISMATCH on {V.tag(pk)} (stored): everything stops, to the user")
            continue
        why = disk_refusal(w.free_gb())
        if why:
            raise SystemExit(why)
        got = {}
        for g in STORED:
            held, audio_sha, finite = w.render(pk, g)
            renders += RENDERS_EACH
            got[g] = {"held": held if finite and isinstance(held, float) and math.isfinite(held) else None,
                      "audio_sha256": audio_sha}
        v = repeat_verdict(got, w.stored[pk])
        rec = {"plan": PLAN, "tag": V.tag(pk), **v, "renders": len(STORED) * RENDERS_EACH,
               "floors_sha256": w.shas["floors"], "answers_sha256": w.shas["answers"], "time": w.now()}
        write_once(rp, rec, V.tag(pk))
        w.log(f"repeat {V.tag(pk)}: holds {v['holds']}")
        if not v["holds"]:
            raise SystemExit(f"REPEAT MISMATCH on {V.tag(pk)}: "
                             f"{[g for g, r in v['guitars'].items() if not r['holds']]}; everything stops, to the user")
    return renders


def wait_repeat(w, wait_s=REPEAT_WAIT_S, poll_s=REPEAT_POLL_S):
    """The other shards: wait (holding no render slot) until both repeat records hold; stop on any that fails, or
    after `wait_s`."""
    t0 = w.clock()
    while True:
        st = repeat_state({k: _read(V.repeat_path(k)) for k in w.check_keys})
        if st == "holds":
            return
        if st == "fails":
            raise SystemExit("REPEAT MISMATCH (another shard's check): everything stops, to the user")
        if w.clock() - t0 >= wait_s:
            raise SystemExit(f"the repeat check did not finish in {wait_s} s (shard {REPEAT_SHARD}/{SHARDS} runs it)")
        w.sleep(poll_s)


def require_repeat(w):
    st = repeat_state({k: _read(V.repeat_path(k)) for k in w.check_keys})
    if st != "holds":
        raise SystemExit(f"the repeat check {st}: --rerun runs only after it held")


def part_record(w, pk, guitars, renders, extra=None):
    return {"plan": PLAN, "tag": V.tag(pk), "guitars": guitars, "renders": renders, **(extra or {}),
            "build_sha256": w.shas["build"], "answers_sha256": w.shas["answers"], "floors_sha256": w.shas["floors"],
            "time": w.now()}


def floor_part(w, pk):
    """The main pass on one part: every rendered guitar in RENDERED's order (carries without a render). -> renders."""
    out, first = V.floor_path(pk), first_path(pk)
    for p_ in (out, first):                              # written once (checked again at the write)
        if p_.exists():
            raise SystemExit(f"{V.tag(pk)}: a floor record exists, never overwritten")
    gs, renders = floor_guitars(ORDER, w.dry_shas(pk), lambda g: w.render(pk, g), w.stored[pk])
    bad = refused_guitars({"guitars": gs})
    write_once(first if bad else out, part_record(w, pk, gs, renders), V.tag(pk))
    w.log(f"{V.tag(pk)}: {'REFUSED ' + str(bad) + ' (--rerun once)' if bad else 'floored'}; {renders} renders; "
          f"carried {[g for g, r in gs.items() if r['carried_from']]}")
    return renders


def rerun_part(w, pk):
    """S1 on one part: its first-pass refused guitars rendered once more (the passing ones taken byte for byte), the
    part's one floors/ record written. -> renders."""
    out, first = V.floor_path(pk), first_path(pk)
    if out.exists():
        raise SystemExit(f"{V.tag(pk)}: a floor record exists, never overwritten")
    rec = json.loads(first.read_text())
    bad = refused_guitars(rec)
    if not bad:
        raise SystemExit(f"{V.tag(pk)}: its first-pass record holds no refusal")
    done = {g: r for g, r in rec["guitars"].items() if g not in bad}
    gs, renders = floor_guitars(bad, w.dry_shas(pk), lambda g: w.render(pk, g), w.stored[pk], done=done, reran=True)
    first_sha = S.file_sha(first)
    write_once(out, part_record(w, pk, gs, rec.get("renders", 0) + renders,
                                {"rerun_renders": renders, "first_sha256": first_sha}), V.tag(pk))
    still = refused_guitars({"guitars": gs})
    w.log(f"{V.tag(pk)}: rerun {bad}; {'still refused ' + str(still) if still else 'passed'}; {renders} renders")
    return renders


def run_floor(args, w):
    """The command's body on a world whose guards already held."""
    shard, rerun = args.shard, bool(getattr(args, "rerun", False))
    total, t0 = 0, w.clock()
    if rerun:
        require_repeat(w)
        todo = [p["pkey"] for p in mine(w.parts, shard)
                if first_path(p["pkey"]).exists() and not V.floor_path(p["pkey"]).exists()]
    else:
        if shard[0] != REPEAT_SHARD:
            wait_repeat(w)
        todo = [p["pkey"] for p in mine(w.parts, shard)
                if not V.floor_path(p["pkey"]).exists() and not first_path(p["pkey"]).exists()]
    if not todo and (rerun or shard[0] != REPEAT_SHARD):
        w.log(f"VOICE FLOORS {'RERUN ' if rerun else ''}{shard[0]}/{shard[1]}: nothing to do")
        return 0
    w.wait_cap()                                         # one render slot for this process
    if not rerun and shard[0] == REPEAT_SHARD:
        total += run_repeat(w)
    for pk in todo:
        why = disk_refusal(w.free_gb())
        if why:
            raise SystemExit(why)
        total += rerun_part(w, pk) if rerun else floor_part(w, pk)
    w.log(f"VOICE FLOORS {'RERUN ' if rerun else ''}DONE {shard[0]}/{shard[1]}: {len(todo)} parts, {total} renders "
          f"in {w.clock() - t0:.0f} s")
    return total


# --- the real world (renders; numpy only after the guards) ------------------------------------------------------------

def require_floors():
    """Every guard, before any render or numpy: main's code and keys and phases (`require_voice`), build.json hashed
    and its proofs held, the stored floors and row (b)'s answers hashed, the build and the stored floors covering the
    draw's parts with every rendered guitar declared. -> the guarded context."""
    m = V.require_voice(V.PHASE_DRY)
    build = V._build(m)
    if build.get("proofs_hold") is not True:
        raise SystemExit("build.json's proofs did not hold: no floors")
    stored, _iv = V._stored_floors(m)
    ans = S.require_hash(S.phase_answers(V.STEM_ROW), S.answers_path(V.STEM_ROW))
    b2 = SE.bank_build(m)
    draw, sd = SE.context()
    keys = sorted(p["pkey"] for p in draw["parts"])
    if len(keys) != V.PARTS or sorted(stored) != keys or sorted(build.get("parts") or {}) != keys:
        raise SystemExit("the draw, the stored floors and the build do not cover the same parts")
    for k in keys:
        gs = (build["parts"][k].get("guitars") or {})
        if any(not (gs.get(g) or {}).get("audio_sha256") or not (gs.get(g) or {}).get("file_sha256") for g in ORDER):
            raise SystemExit(f"{V.tag(k)}: build.json does not declare every rendered guitar's sha256")
        if any(not S.finite_pos((stored[k].get(g) or {}).get("held")) for g in STORED):
            raise SystemExit(f"{V.tag(k)}: a stored floor is not finite and positive")
        if k not in (ans.get("parts") or {}):
            raise SystemExit(f"{V.tag(k)}: row (b) has no answer")
    shas = {"build": S.file_sha(V.build_path()), "floors": S.file_sha(SE.floors_path()),
            "answers": S.file_sha(S.answers_path(V.STEM_ROW))}
    return {"m": m, "build": build, "stored": stored, "answers": ans, "b2": b2, "draw": draw, "sd": sd,
            "shas": shas}


def dry_file(g, pk):
    """Where a rendered guitar's dry file sits: the build's four under PF/fs/voice/dry/, avg+mild the replay's blur."""
    if g == V.AVG_MILD:
        from learn import note_replay as R

        return R.blur_path(V.AVG_MILD, pk)
    return V.dry_path(g, pk)


class RealWorld:
    """The renders and files of the floors, on a guarded context (`require_floors`)."""

    def __init__(self, ctx):
        self.ctx, self.parts, self.stored, self.shas = ctx, ctx["draw"]["parts"], ctx["stored"], ctx["shas"]
        self.check_keys = V.check_parts(self.parts)
        if len(self.check_keys) != V.CHECK_PARTS:
            raise SystemExit("the draw does not give the two check parts")
        self._part, self._key = None, None

    @staticmethod
    def log(msg):
        print(msg, flush=True)

    @staticmethod
    def now():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def clock():
        return time.time()

    @staticmethod
    def sleep(s):
        time.sleep(s)

    @staticmethod
    def free_gb():
        from learn import pretrain_set as PS

        return PS.free_gb()

    @staticmethod
    def wait_cap():
        from learn import local_objective as LO
        from learn import note_replay as R

        R.no_separation_beside()
        LO._wait_cap()

    def _context(self, pk):
        """A part's judge DI, clean record, answer and the stored guitars' audio, loaded once a part."""
        if self._key == pk:
            return self._part
        import numpy as np

        from learn import local_objective as LO
        from learn import note_replay as R
        from learn import note_transcribe as NT
        from learn import pipeline_fix as P

        p = next(q for q in self.parts if q["pkey"] == pk)
        prt = self.ctx["sd"].units[(p["set"], p["unit"], p["amp"])]["prt"]
        di32 = R.di_section(prt)
        lo, hi = SE._trim()
        a = self.ctx["answers"]["parts"][pk]
        self._part = {"p": p, "di32": di32, "di": np.asarray(di32, np.float64)[lo:hi], "trim": (lo, hi),
                      "clean": P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]),
                      "select": a["select"], "x": LO.tdict(a["answer"]),
                      "stored32": {"true": di32, SE.BANK_ARM: NT.load_dry(SE.BANK_ARM, pk, self.ctx["b2"])}}
        self._key = pk
        return self._part

    def dry_shas(self, pk):
        """{guitar: dry sha256}: the rendered guitars' as build.json declares them, the stored ones' from audio."""
        c = self._context(pk)
        out = {g: self.ctx["build"]["parts"][pk]["guitars"][g]["audio_sha256"] for g in ORDER}
        out.update({g: S.npy_sha(x) for g, x in c["stored32"].items()})
        return out

    def load(self, pk, g):
        """A guitar's dry audio, float32: the stored ones as stored; a rendered one refused unless its file and samples
        are build.json's."""
        c = self._context(pk)
        if g in STORED:
            return c["stored32"][g]
        import numpy as np

        ent = self.ctx["build"]["parts"][pk]["guitars"][g]
        path = dry_file(g, pk)
        if not path.exists() or S.file_sha(path) != ent["file_sha256"]:
            raise SystemExit(f"{V.tag(pk)}: {g}'s file is not build.json's")
        x32 = np.load(path).astype(np.float32)
        if S.npy_sha(x32) != ent["audio_sha256"]:
            raise SystemExit(f"{V.tag(pk)}: {g}'s samples are not build.json's")
        return x32

    def render(self, pk, g):
        """Row (b)'s answer through a guitar in a fresh primed process (`audibility_measure.fresh_render`), the held
        half judged against the clean record with the true DI as the judge's DI at the part's lag. -> (held, render
        sha256, finite)."""
        import numpy as np

        from learn import audibility_measure as AM
        from learn import cc_build as CB
        from learn import note_replay as R

        c = self._context(pk)
        x32 = self.load(pk, g)
        lo, hi = c["trim"]
        y = np.asarray(AM.fresh_render(CB.new_renderer, x32, c["select"], c["x"], c["x"]), np.float64)[lo:hi]
        finite = bool(np.isfinite(y).all())
        dh = R.half_distance(c["clean"], y, c["di"], c["p"]["lag"], c["p"]["held"]) if finite else math.inf
        return float(dh), AM.audio_sha(np.nan_to_num(y)), finite


def open_world():
    """The guards, then the real world."""
    return RealWorld(require_floors())


def cmd_floor(args):
    """The floors of one shard (`run_floor`): the shard checked, every guard before any render."""
    why = shard_refusal(getattr(args, "shard", None))
    if why:
        raise SystemExit(why)
    w = open_world()
    return run_floor(args, w)


COMMANDS = {"floor": cmd_floor}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=S._shard, required=True, help=f"k/{SHARDS}: one render process a shard")
    ap.add_argument("--rerun", action="store_true",
                    help="S1: only the parts whose first pass refused, their refused guitars once more")
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
