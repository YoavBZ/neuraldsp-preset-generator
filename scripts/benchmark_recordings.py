#!/usr/bin/env python3
"""Match real amp recordings, heard through their own DI.

    python scripts/benchmark_recordings.py --renderer swift --pack morgan --amp sw50r \\
      --signal same --signal other --signal noise --budget 300 --workers 2 \\
      --json recordings-sw50r.json

Every usable development part of `docs/validation-datasets.md` is a target (with
`--set`, only those of the named validation sets; the runs recorded in
`tone-matching-plan.md` predate the second set and are `--set 1`): its
amp track (a real amplifier, or for Cambridge a processed guitar track) is the
reference, and its own DI is what every answer is rendered through to be scored —
what the player hears. Each `--signal` runs the same pipeline (neutral settings,
inversion, search) through a different signal, with the same budget and random
numbers, starting from the pack's neutral settings for `--amp` with its switches
and selectors held:

  same    the part's own DI: a same-take DI, the best case
  other   the DI of the next usable part from a different session. For
          Guitar-TECHS that is another excerpt of the same player and rig, and
          for Telefunken often the same band and room, not another player
  noise   the synthetic noise-burst probe match_preset.py uses with no DI
  library one 6-second probe of real guitar: the loudest 1.5 s of four
          development DIs from bands other than the part's own (catalog `group`),
          each set to the median development-DI loudness, with short fades

`--no-search` scores only the neutral start and each signal's inversion (the
calculated EQ and level, a handful of renders): what a deterministic,
search-free match would give.

Each part's declared 10-second excerpt is cut by `build_validation_crops.py` into
private WAVs under `--crops-dir` (built once, then reused after checking their
hashes). The catalog is always the committed `docs/validation-datasets.json`,
and held-out parts are refused: this is a development benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shlex
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, positive_int, probe_di
from benchmark_match import _backend_caveat, _renderer, _source_commit

SCHEMA = "recordings-benchmark-1"
CATALOG = PLUGIN_ROOT / "docs" / "validation-datasets.json"
SIGNALS = ("same", "other", "noise", "library")
# The `library` signal: a fixed probe of real guitar, built per part from
# development DIs of other bands, so no part is ever heard through its own band's
# playing (docs/research-song-only-matching.md, approach 1).
LIBRARY_CLIPS = 4
LIBRARY_CLIP_SECONDS = 1.5
LIBRARY_FADE_SECONDS = 0.05
LIBRARY_LUFS = -22.9   # the median loudness of the 43 set-2 development DIs
NO_DI_SECONDS = 6.0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", default="morgan")
    ap.add_argument("--amp", required=True)
    ap.add_argument("--renderer", choices=("synthetic", "swift"), default="synthetic")
    ap.add_argument("--signal", action="append", required=True, choices=SIGNALS,
                    help="repeatable; the first is the reference the others pair with")
    ap.add_argument("--budget", type=positive_int, default=300)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--loss-profile", default="unpaired-v2")
    ap.add_argument("--workers", type=positive_int, default=1)
    ap.add_argument("--part", action="append", metavar="SOURCE/SONG/PART",
                    help="only these development parts (default: every usable one)")
    ap.add_argument("--set", type=int, choices=(1, 2), action="append", dest="sets",
                    help="repeatable; only parts of these validation sets (default: all)")
    ap.add_argument("--data-root", type=pathlib.Path,
                    help="dataset root (default: the catalog's)")
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"),
                    help="private directory for the 10-second crops")
    ap.add_argument("--no-search", action="store_true",
                    help="score the neutral start and each signal's inversion only")
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def development_parts(catalog: dict, only=None, sets=None):
    """(source, song, part) for every usable development part, in catalog order.

    A session without a `set` is from the first set, declared before there was one.
    """
    parts = [(session["source"], session["song"], part["part"])
             for session in catalog["sessions"] if session["split"] == "development"
             and (not sets or session.get("set", 1) in sets)
             for part in session["parts"] if part.get("usable")]
    if only:
        wanted = [tuple(item.split("/", 2)) for item in only]
        missing = [item for item in wanted if item not in parts]
        if missing:
            die(f"not usable development parts: {', '.join('/'.join(m) for m in missing)}")
        parts = [item for item in parts if item in wanted]
    return parts


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def crops_for(catalog_path, data_root, crops_dir, source, song, part):
    """The part's crop record, building it once and verifying it after.

    A cached record must name this part, the catalog must still list its
    session as development, every source file the crop was cut from must have
    the hash the catalog lists for it, the part's DI, amp tracks and the
    session's guitar DIs must be the ones it was cut with — and, for a session
    that declares its mix, its mix and vocal tracks — and its outputs must match
    their hashes.
    The catalog file itself may have changed since — its held-out ledger grows
    with every declared test — without making the crop stale.
    """
    from build_validation_crops import build

    slug = "-".join(piece.replace("/", "_").replace(" ", "_")
                    for piece in (source, song, part))
    out_dir = crops_dir.expanduser() / slug
    record_path = out_dir / "record.json"
    if not record_path.exists():
        build(catalog_path, data_root, source, song, part, out_dir)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    catalog = json.loads(pathlib.Path(catalog_path).read_text(encoding="utf-8"))
    sessions = [item for item in catalog["sessions"]
                if item["source"] == source and item["song"] == song]
    session = sessions[0] if len(sessions) == 1 else {"parts": []}
    entries = [item for item in session["parts"] if item.get("part") == part]
    entry = entries[0] if len(entries) == 1 else {}
    files = session.get("files", {})
    expected = {"source": source, "song": song, "part": part, "split": "development"}
    found = {key: record.get(key) for key in expected}
    cut_from = record.get("verified_source_sha256") or {}
    roles_kept = (bool(entry)
                  and {entry.get("di"), entry.get("reference")} <= cut_from.keys()
                  and record.get("removed_own_amp_tracks") == sorted(
                      {entry.get("reference"), *entry.get("alternate", [])})
                  and record.get("excluded_guitar_dis") == sorted(
                      {item["di"] for item in session["parts"] if item.get("di")})
                  and ("mix_tracks" not in session
                       or (record.get("included_mix_tracks") == session["mix_tracks"]
                           and record.get("vocal_tracks") == sorted(
                               session.get("vocal_tracks") or ()))))
    if (found != expected or session.get("split") != "development" or not cut_from
            or any(files.get(name) != digest for name, digest in cut_from.items())
            or not roles_kept):
        die(f"{record_path} was not cut from this catalog for {source}/{song}/{part}; "
            f"delete {out_dir} to rebuild it")
    for role, output in record["outputs"].items():
        if _sha(output["path"]) != output["sha256"]:
            die(f"{output['path']} no longer matches its crop record; delete {out_dir} "
                f"to rebuild it")
    return record


def part_groups(catalog: dict, parts) -> list:
    """Each part's band: the catalog's `group`, else its own session."""
    by_session = {(session["source"], session["song"]): session.get("group")
                  for session in catalog["sessions"]}
    return [by_session.get(tuple(part[:2])) or "/".join(part[:2]) for part in parts]


def library_probe(index, parts, dis, groups, rate=48000):
    """A fixed probe of real guitar for one part, never from the part's own band.

    Walks the parts after this one in catalog order, alternating between the
    other source and the part's own (so a probe is not all one recording chain,
    as a public library would not be), and takes the loudest
    LIBRARY_CLIP_SECONDS of each DI from a band not yet used and not the part's
    own, until it has LIBRARY_CLIPS clips. Each clip is set to LIBRARY_LUFS and
    faded in and out. Returns the samples and the parts the clips came from.
    """
    import numpy as np

    from analysis import io

    length = int(LIBRARY_CLIP_SECONDS * rate)
    fade = np.linspace(0.0, 1.0, int(LIBRARY_FADE_SECONDS * rate))
    hop = rate // 4

    def clip_of(other):
        di = np.asarray(dis[other], dtype=np.float64)
        if len(di) < length:
            return None
        energies = [float(np.mean(di[start:start + length] ** 2))
                    for start in range(0, len(di) - length + 1, hop)]
        start = int(np.argmax(energies)) * hop
        clip = di[start:start + length].copy()
        lufs = io.loudness_lufs(io.from_samples(clip, rate))
        if lufs is None:
            return None
        clip *= 10 ** ((LIBRARY_LUFS - lufs) / 20)
        clip[:len(fade)] *= fade
        clip[-len(fade):] *= fade[::-1]
        return clip

    clips, used, sources = [], {groups[index]}, []
    walk = [(index + step) % len(parts) for step in range(1, len(parts))]
    queues = [[i for i in walk if parts[i][0] != parts[index][0]],
              [i for i in walk if parts[i][0] == parts[index][0]]]
    turn = 0
    while len(clips) < LIBRARY_CLIPS and any(queues):
        queue = queues[turn % 2] if queues[turn % 2] else queues[(turn + 1) % 2]
        turn += 1
        while queue:
            other = queue.pop(0)
            if groups[other] in used:
                continue
            clip = clip_of(other)
            if clip is None:
                continue
            clips.append(clip)
            used.add(groups[other])
            sources.append("/".join(parts[other]))
            break
    if len(clips) < LIBRARY_CLIPS:
        die(f"the library signal needs {LIBRARY_CLIPS} other bands for "
            f"{'/'.join(parts[index])}")
    return np.concatenate(clips).astype(np.float32), sources


def other_di_index(parts, index):
    """The next part, cyclically, from a different session."""
    for step in range(1, len(parts)):
        candidate = (index + step) % len(parts)
        if parts[candidate][:2] != parts[index][:2]:
            return candidate
    return None


def main() -> None:
    args = build_parser().parse_args()
    if len(set(args.signal)) != len(args.signal):
        die("each --signal once")

    from analysis import io, require

    require("running the recordings benchmark")
    import numpy as np

    from match import invert, signal_benchmark, space as space_module

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    data_root = (args.data_root or pathlib.Path(catalog["root"])).expanduser()
    parts = development_parts(catalog, args.part, args.sets)
    if not parts:
        die("no usable development parts selected")
    records = [crops_for(CATALOG, data_root, args.crops_dir, *part)
               for part in parts]
    load = lambda path: io.load(path).mono()
    dis = [load(record["outputs"]["di"]["path"]) for record in records]
    references = [load(record["outputs"]["reference"]["path"]) for record in records]
    noise, _ = probe_di(None, NO_DI_SECONDS)
    libraries = [None] * len(parts)
    if "library" in args.signal:
        # Drawn from every development part of the chosen sets, whichever parts
        # are scored, so `--part` does not shrink the library.
        pool = development_parts(catalog, None, args.sets)
        pool_dis = [load(crops_for(CATALOG, data_root, args.crops_dir, *part)
                         ["outputs"]["di"]["path"]) for part in pool]
        pool_groups = part_groups(catalog, pool)
        libraries = [library_probe(pool.index(part), pool, pool_dis, pool_groups)
                     for part in parts]
    others = [other_di_index(parts, index) for index in range(len(parts))]
    if "other" in args.signal and any(other is None for other in others):
        die("--signal other needs parts from at least two sessions")
    recordings = []
    for index in range(len(parts)):
        by_name = {"same": dis[index],
                   "other": dis[others[index]] if others[index] is not None else None,
                   "noise": noise,
                   "library": libraries[index] and libraries[index][0]}
        recordings.append({"reference": references[index], "di": dis[index],
                           "signals": {name: by_name[name] for name in args.signal}})

    try:
        amp = invert.resolve_signal_path(args.pack, args.amp)
    except invert.InversionError as error:
        die(str(error))
    space = space_module.build(args.pack, amp=amp)
    renderer = _renderer(args.renderer, args.pack)
    try:
        metadata = renderer.metadata()
        topology = signal_benchmark.fixed_topology(space, amp, None,
                                                   renderer.parameter_specs())
        started = time.time()

        def progress(done, total):
            print(f"  part {done}/{total} — {time.time() - started:.0f}s elapsed",
                  file=sys.stderr, flush=True)

        outcomes = signal_benchmark.compare_search_signals(
            renderer, space, None, {}, topology, budget=args.budget,
            profile=args.loss_profile, rng=np.random.default_rng(args.seed),
            pack_id=args.pack, amp=amp, progress=progress, workers=args.workers,
            renderer_factory=(None if args.workers < 2
                              else lambda: _renderer(args.renderer, args.pack)),
            recordings=recordings, run_search=not args.no_search)
    finally:
        close = getattr(renderer, "close", None)
        if close is not None:
            close()

    reference = args.signal[0]
    summary = signal_benchmark.summarise(outcomes, reference)
    elapsed = time.time() - started
    caveat = _backend_caveat(metadata)
    print(f"\n{len(parts)} development parts, budget {args.budget}, {args.pack}/{amp}, "
          f"{metadata.renderer_id} {metadata.plugin_version}, {args.loss_profile}, "
          f"{elapsed:.0f}s; answers heard through each part's own DI\n")
    for name, entry in summary.items():
        versus = ""
        if "closer_than_reference" in entry:
            versus = (f" | closer than {reference} on {entry['closer_than_reference']}"
                      f"/{entry['paired_targets']}, "
                      f"{100 * entry['mean_change_fraction']:+.0f}%")
        neutral = entry.get("against_neutral") or {}
        print(f"{name:6} answer {entry['objective_mean']} / {entry['objective_median']}"
              f" | inversion alone {entry['inversion_objective_mean']}"
              f" | closer than neutral on {neutral.get('closer')}/{neutral.get('targets')}"
              + versus)
    print(f"neutral start {summary[reference]['neutral_objective_mean']} / "
          f"{summary[reference]['neutral_objective_median']}")
    if caveat:
        print(f"\n  {caveat}.")

    if args.json:
        args.json.write_text(json.dumps({
            "schema": SCHEMA,
            "source_commit": _source_commit(),
            "command": " ".join(shlex.quote(arg) for arg in sys.argv),
            "elapsed_s": round(elapsed, 1),
            "catalog_sha256": _sha(CATALOG),
            "pack": args.pack, "amp": amp, "signals": args.signal,
            "search": not args.no_search,
            "reference": reference, "budget": args.budget, "seed": args.seed,
            "loss_profile": args.loss_profile, "workers": args.workers,
            "no_di_seconds": NO_DI_SECONDS,
            "parts": [{"source": source, "song": song, "part": part,
                       "other_di_from": ("/".join(parts[others[index]])
                                         if others[index] is not None else None),
                       "crops": {role: output["sha256"] for role, output
                                 in record["outputs"].items()},
                       "excerpt_start_s": record["excerpt_start_s"],
                       "library_from": (libraries[index][1]
                                        if libraries[index] else None)}
                      for index, ((source, song, part), record)
                      in enumerate(zip(parts, records))],
            "backend": metadata.as_dict(), "measurement_caveat": caveat or None,
            "summary": summary,
            "outcomes": [vars(outcome) for outcome in outcomes],
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    guarded(main)
