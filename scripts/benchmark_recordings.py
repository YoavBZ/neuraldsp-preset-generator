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
          each set to the median development-DI loudness, with short fades;
          with `--library-from other-source`, only from bands of the other
          source, so no clip shares the part's dataset (studio or library)

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
# One measured DI-to-amp-track lag per development part (scripts/record_part_lags.py);
# the catalogue's `lag_ms` is quantised to 10 ms and wrong on about one part in five.
LAGS = PLUGIN_ROOT / "docs" / "validation-lags.json"
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
    ap.add_argument("--library-from", choices=("other-bands", "other-source"),
                    default="other-bands",
                    help="the library's clips: any other band (default), or only "
                         "bands of another source than the part's own")
    ap.add_argument("--no-search", action="store_true",
                    help="score the neutral start and each signal's inversion only")
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def lag_samples(part: str, lags_path: pathlib.Path = LAGS):
    """Samples the part's amp track lags its DI at 48 kHz (recording[t] ~ di[t - lag]),
    as measured once and recorded; None if the part has no recorded lag. Ambiguous
    lags (two correlation peaks) are returned too; `lag_record` says which."""
    record = lag_record(part, lags_path)
    return None if record is None else record["lag_samples"]


def lag_record(part: str, lags_path: pathlib.Path = LAGS):
    """The part's whole recorded entry (lag, stability, ambiguity), or None."""
    if not lags_path.exists():
        return None
    return json.loads(lags_path.read_text())["parts"].get(part)


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


def library_probe(target, pool, dis, groups, exclude=(), rate=48000,
                  other_source_only=False):
    """A fixed probe of real guitar for one part, never from its own band.

    The bands other than the part's own (and any in `exclude`) are split into the
    part's own source and the other source, each put in an order seeded by the
    part's id, and taken alternately, the other source first, so no probe is one
    recording chain. From each band one of its DIs, also chosen by that seed,
    gives its loudest LIBRARY_CLIP_SECONDS (0.25 s hops), set to LIBRARY_LUFS and
    faded in and out; a DI too short or unmeasurable passes to the band's next.
    LIBRARY_LUFS is the median of whole development crops, so each clip, the
    busiest stretch of its DI, plays about 1 LU softer than its own crop's busiest
    stretch would. With `other_source_only` the part's own source contributes
    nothing, so no clip shares its dataset (for set 2, its studio or library).
    Returns the samples and the parts the clips came from.
    """
    import random

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

    index = pool.index(target)
    rng = random.Random("/".join(target))
    members = {}
    for i, part in enumerate(pool):
        if groups[i] != groups[index] and groups[i] not in exclude:
            members.setdefault(groups[i], []).append(i)
    source_of = {group: pool[items[0]][0] for group, items in members.items()}
    queues = []
    for own in (False, True):
        bands = sorted(g for g in members if (source_of[g] == target[0]) == own
                       and not (own and other_source_only))
        rng.shuffle(bands)
        queues.append(bands)
    clips, sources, turn = [], [], 0
    while len(clips) < LIBRARY_CLIPS and any(queues):
        queue = queues[turn % 2] if queues[turn % 2] else queues[(turn + 1) % 2]
        turn += 1
        while queue:
            band = queue.pop(0)
            candidates = members[band][:]
            first = rng.randrange(len(candidates))
            for other in candidates[first:] + candidates[:first]:
                clip = clip_of(other)
                if clip is not None:
                    clips.append(clip)
                    sources.append("/".join(pool[other]))
                    break
            else:
                continue
            break
    if len(clips) < LIBRARY_CLIPS:
        die(f"the library signal needs {LIBRARY_CLIPS} other bands for {'/'.join(target)}")
    return np.concatenate(clips).astype(np.float32), sources


def inversion_pairs(outcomes, reference: str, profile: str) -> dict:
    """Without a search, what a match is: each signal's inversion, paired by part
    against the neutral start and against the reference signal's inversion, with
    and without the `level` term (the research plan's E1 gates)."""
    import statistics

    from analysis.compare import Objectives, scalar
    from scipy.stats import wilcoxon

    def without_level(dimensions):
        if not dimensions:
            return None
        return scalar(Objectives(values={k: v for k, v in dimensions.items()
                                         if k != "level"}, profile=profile))

    rows = {}
    for outcome in outcomes:
        if not outcome.failed and outcome.inversion_objective is not None:
            rows.setdefault(outcome.signal, {})[outcome.target_index] = outcome

    def pair(mine, theirs):
        both = [(a, b) for a, b in zip(mine, theirs) if a is not None and b is not None]
        if not both:
            return None
        diffs = [a - b for a, b in both]
        result = {"targets": len(both), "closer": sum(a < b for a, b in both),
                  "median_change_fraction": round(statistics.median(
                      a / b - 1 for a, b in both if b), 4)}
        if any(diffs) and len(both) > 1:
            result["wilcoxon_p"] = float(wilcoxon([a for a, _ in both],
                                                  [b for _, b in both]).pvalue)
        return result

    pairs = {}
    for signal, mine in rows.items():
        keys = sorted(mine)
        entry = {
            "against_neutral": pair([mine[k].inversion_objective for k in keys],
                                    [mine[k].neutral_objective for k in keys]),
            "against_neutral_no_level": pair(
                [without_level(mine[k].inversion_dimensions) for k in keys],
                [without_level(mine[k].neutral_dimensions) for k in keys])}
        if signal != reference and reference in rows:
            theirs = rows[reference]
            common = [k for k in keys if k in theirs]
            entry[f"against_{reference}"] = pair(
                [mine[k].inversion_objective for k in common],
                [theirs[k].inversion_objective for k in common])
            entry[f"against_{reference}_no_level"] = pair(
                [without_level(mine[k].inversion_dimensions) for k in common],
                [without_level(theirs[k].inversion_dimensions) for k in common])
        pairs[signal] = entry
    return pairs


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
    if args.library_from != "other-bands" and "library" not in args.signal:
        die("--library-from shapes the library signal: add --signal library")

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
    others = [other_di_index(parts, index) for index in range(len(parts))]
    groups = part_groups(catalog, parts)
    libraries = [None] * len(parts)
    if "library" in args.signal:
        # Drawn from every set-2 development part, whichever parts are scored, so
        # `--part` does not shrink it; set 1 (one Guitar-TECHS player and rig,
        # and the bands without a catalog group) stays out, as the research plan
        # says. The `other` DI's band is left out too, so the two arms do not
        # share a recording.
        pool = development_parts(catalog, None, [2])
        missing = [part for part in parts if part not in pool]
        if missing:
            die("--signal library scores set-2 development parts only: "
                + ", ".join("/".join(part) for part in missing))
        pool_dis = [load(crops_for(CATALOG, data_root, args.crops_dir, *part)
                         ["outputs"]["di"]["path"]) for part in pool]
        pool_groups = part_groups(catalog, pool)
        # With the library on, `other` is chosen over the whole pool too, so
        # neither arm changes with which parts `--part` scores.
        pool_others = [pool[other_di_index(pool, pool.index(part))] for part in parts]
        other_dis = [pool_dis[pool.index(part)] for part in pool_others]
        libraries = [library_probe(part, pool, pool_dis, pool_groups,
                                   exclude={pool_groups[pool.index(pool_others[index])]},
                                   other_source_only=args.library_from == "other-source")
                     for index, part in enumerate(parts)]
    if ("other" in args.signal and "library" not in args.signal
            and any(other is None for other in others)):
        die("--signal other needs parts from at least two sessions")
    recordings = []
    for index in range(len(parts)):
        other_di = (other_dis[index] if "library" in args.signal
                    else dis[others[index]] if others[index] is not None else None)
        by_name = {"same": dis[index],
                   "other": other_di,
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
    if args.no_search:
        for name, entry in inversion_pairs(outcomes, reference, args.loss_profile).items():
            summary.setdefault(name, {})["inversion_pairs"] = entry
    elapsed = time.time() - started
    caveat = _backend_caveat(metadata)
    print(f"\n{len(parts)} development parts, "
          f"{'no search' if args.no_search else f'budget {args.budget}'}, {args.pack}/{amp}, "
          f"{metadata.renderer_id} {metadata.plugin_version}, {args.loss_profile}, "
          f"{elapsed:.0f}s; answers heard through each part's own DI\n")
    for name, entry in summary.items():
        if args.no_search:
            pairs = entry.get("inversion_pairs") or {}

            def said(key):
                found = pairs.get(key)
                return "n/a" if not found else (
                    f"{found['closer']}/{found['targets']}, "
                    f"{100 * found['median_change_fraction']:+.0f}%"
                    + (f", p={found['wilcoxon_p']:.2g}" if "wilcoxon_p" in found else ""))

            print(f"{name:8} inversion {entry.get('inversion_objective_mean')} / "
                  f"{entry.get('inversion_objective_median')} | closer than neutral "
                  f"{said('against_neutral')} (no level {said('against_neutral_no_level')})"
                  + ("" if name == reference else
                     f" | closer than {reference} {said(f'against_{reference}')} "
                     f"(no level {said(f'against_{reference}_no_level')})"))
            continue
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
            "search": not args.no_search, "library_from_mode": args.library_from,
            "reference": reference, "budget": args.budget, "seed": args.seed,
            "loss_profile": args.loss_profile, "workers": args.workers,
            "no_di_seconds": NO_DI_SECONDS,
            "parts": [{"source": source, "song": song, "part": part,
                       "other_di_from": ("/".join(pool_others[index])
                                         if "library" in args.signal
                                         else "/".join(parts[others[index]])
                                         if others[index] is not None else None),
                       "crops": {role: output["sha256"] for role, output
                                 in record["outputs"].items()},
                       "excerpt_start_s": record["excerpt_start_s"],
                       "group": groups[index],
                       "library_from": (libraries[index][1]
                                        if libraries[index] else None),
                       "library_sha256": (hashlib.sha256(
                           libraries[index][0].tobytes()).hexdigest()
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
