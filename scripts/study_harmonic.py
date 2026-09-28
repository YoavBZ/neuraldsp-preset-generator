#!/usr/bin/env python3
"""Does the fingerprint's harmonic dimension measure the amp on a played passage?

    python scripts/study_harmonic.py --renderer swift --pack morgan --amp sw50r \\
      --di howlong=how-long-di-6s.wav --di hotel=hotel-di-6s.wav --development-dis \\
      --recordings docs/recordings-benchmark-sw50r.json --json harmonic-sw50r.json

`analysis.features.harmonic` finds the longest steady single note in a signal
(autocorrelation pitch between 60 and 1200 Hz) and measures three things on it:
harmonic-to-noise ratio, odd- against even-harmonic power and high-frequency
fizz. `analysis.compare` turns them into the `harmonic` dimension. The questions:

- **pairs** (no plugin): each usable development part of
  `validation-datasets.md` is one take recorded twice, as a DI and through an
  amp. Does the note the harmonic features are measured on come out the same on
  both sides, and how often does the pitch sit on an edge of its search range?
- **tracks**: the amp's neutral settings driven from clean to dirty
  (`STEPS`), rendered through every passage. Within a passage, how far does the
  `harmonic` dimension move between a setting and the middle step; at one
  setting, how far does it move between two passages? A dimension that measures
  the amp moves with the setting more than with the playing. Every render of
  the middle step is made twice, for the render-to-render noise.
- **rescored** (with --recordings): the recordings benchmark's comparisons with
  the `harmonic` dimension left out of every total.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import pathlib
import shlex
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded
from benchmark_match import _backend_caveat, _renderer, _source_commit

SCHEMA = "harmonic-study-1"
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops")
PITCH_RANGE_HZ = (60.0, 1200.0)   # analysis.features._monophonic_segment's
SAME_NOTE = 0.03                  # two pitches within 3% are one note

# Clean to dirty from the neutral start, per signal path: the preamp volume
# stepped up, then a drive pedal in front of the middle step. The middle
# (reference) step is the one every other is compared with.
STEPS = {
    ("morgan", "sw50r"): [(f"volume {v}", {"sw50rAmp/sw50rVolume": float(v)})
                          for v in (10, 30, 50, 70, 90)]
    + [(f"volume 50 + drive {d}", {"sw50rAmp/sw50rVolume": 50.0,
                                   "drive1/drive1Active": True,
                                   "drive1/drive1Drive": float(d)}) for d in (50, 100)],
    ("toneking", "rhythm"): [(f"volume {v}", {"rhythmAmpVolume": v})
                             for v in (0.1, 0.3, 0.5, 0.7, 0.9)]
    + [(f"volume 0.5 + drive {d}", {"rhythmAmpVolume": 0.5, "drive1Active": True,
                                    "drive1Overdrive": d}) for d in (0.5, 1.0)],
}
REFERENCE_STEP = 2


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", default="morgan")
    ap.add_argument("--amp", required=True)
    ap.add_argument("--renderer", choices=("synthetic", "swift"), default="synthetic")
    ap.add_argument("--di", action="append", default=[], metavar="NAME=PATH",
                    help="a played passage; repeatable")
    ap.add_argument("--development-dis", action="store_true",
                    help="also every usable development part's DI crop, and ask "
                         "the pairs question of those parts")
    ap.add_argument("--crops-dir", type=pathlib.Path, default=CROPS)
    ap.add_argument("--recordings", type=pathlib.Path, action="append", default=[],
                    help="a recordings-benchmark JSON to rescore without `harmonic`")
    ap.add_argument("--loss-profile", default="unpaired-v2")
    ap.add_argument("--json", type=pathlib.Path)
    return ap


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def measure(audio, sample_rate):
    """The fingerprint and the note its harmonic features were measured on."""
    from analysis import features, io
    from analysis.fingerprint import fingerprint

    printed = fingerprint(io.from_samples(audio, sample_rate), regime="isolated_stem",
                          excerpt_s=None)
    import numpy as np

    mono = np.asarray(audio, dtype=np.float64)
    if mono.ndim > 1:
        mono = mono.mean(axis=1)
    segment = features._monophonic_segment(mono, sample_rate)
    harmonic = printed.harmonic
    note = None
    if segment is not None:
        start, stop, f0, _ = segment
        note = {"start_s": round(start / sample_rate, 3),
                "stop_s": round(stop / sample_rate, 3), "f0_hz": round(float(f0), 1),
                "at_edge": any(abs(f0 - edge) / edge < 0.01 for edge in PITCH_RANGE_HZ)}
    return printed, {
        "note": note,
        **{key: None if harmonic.get(key) is None else round(float(harmonic[key]), 4)
           for key in ("hnr_db", "odd_even_ratio", "hf_residual_index", "confidence")}}


def same_note(a, b) -> bool:
    if a is None or b is None:
        return False
    return abs(a["f0_hz"] - b["f0_hz"]) <= SAME_NOTE * min(a["f0_hz"], b["f0_hz"])


def pairs_question(records, profile):
    from analysis import io
    from analysis.compare import compare

    rows = []
    for (source, song, part), record in records:
        di_print, di = measure(io.load(record["outputs"]["di"]["path"]).mono(),
                               io.SAMPLE_RATE)
        amp_print, amp = measure(
            io.load(record["outputs"]["reference"]["path"]).mono(), io.SAMPLE_RATE)
        rows.append({"part": f"{source}/{song}/{part}", "di": di, "amp": amp,
                     "same_note": same_note(di["note"], amp["note"]),
                     "harmonic": compare(amp_print, di_print,
                                         profile=profile).values.get("harmonic")})
    return rows


def rescore(path, profile):
    """The recordings benchmark's comparisons, with and without `harmonic`."""
    from scipy import stats

    from analysis.compare import load_profile

    document = json.loads(path.read_text(encoding="utf-8"))
    weights = load_profile(profile)["weights"]

    def total(dimensions, drop):
        used = {name: value for name, value in dimensions.items()
                if name not in drop and weights.get(name, 0) > 0 and value is not None}
        return sum(weights[n] * v for n, v in used.items()) / sum(weights[n] for n in used)

    by = {}
    for outcome in document["outcomes"]:
        by.setdefault(outcome["signal"], {})[outcome["target_index"]] = outcome
    indices = sorted(by["same"])
    arms = {name: lambda drop, n=name: [total(by[n][i]["objective_dimensions"], drop)
                                        for i in indices] for name in by}
    arms["neutral"] = lambda drop: [total(by["same"][i]["neutral_dimensions"], drop)
                                    for i in indices]

    def paired(a, b, drop):
        x, y = arms[a](drop), arms[b](drop)
        closer = sum(p < q for p, q in zip(x, y))
        change = (statistics.fmean(x) - statistics.fmean(y)) / statistics.fmean(y)
        p = float(stats.wilcoxon(x, y).pvalue) if any(p != q for p, q in zip(x, y)) else 1.0
        return {"closer": closer, "of": len(x), "mean_change": round(change, 3),
                "p": round(p, 4)}

    comparisons = [(a, b) for a, b in (("same", "other"), ("other", "noise"),
                                       ("same", "neutral"), ("other", "neutral"),
                                       ("noise", "neutral")) if a in arms and b in arms]
    return {"path": str(path), "sha256": _sha(path), "amp": document.get("amp"),
            "rows": [{"a": a, "b": b,
                      "with_harmonic": paired(a, b, ()),
                      "without_harmonic": paired(a, b, ("harmonic",)),
                      "without_harmonic_or_level": paired(a, b, ("harmonic", "level"))}
                     for a, b in comparisons]}


def main() -> None:
    args = build_parser().parse_args()

    from analysis import io, require

    require("running the harmonic study")
    import numpy as np

    from analysis.compare import compare
    from match import invert, search, signal_benchmark, space as space_module

    try:
        amp = invert.resolve_signal_path(args.pack, args.amp)
    except invert.InversionError as error:
        die(str(error))
    if (args.pack, amp) not in STEPS:
        die(f"drive steps are defined for {', '.join('/'.join(k) for k in STEPS)}, "
            f"not {args.pack}/{amp}")
    commit = _source_commit()
    dis, described = {}, {}
    for spec in args.di:
        name, _, path = spec.partition("=")
        if not name or not path or name in dis:
            die(f"--di {spec!r}: give each as a distinct NAME=PATH")
        dis[name] = io.load(path).mono()
        described[name] = {"path": path, "sha256": _sha(path)}
    records = []
    if args.development_dis:
        import benchmark_recordings as recordings

        catalog = json.loads(recordings.CATALOG.read_text(encoding="utf-8"))
        root = pathlib.Path(catalog["root"]).expanduser()
        for part in recordings.development_parts(catalog):
            record = recordings.crops_for(recordings.CATALOG, root, args.crops_dir, *part)
            records.append((part, record))
            name = "/".join(part)
            dis[name] = io.load(record["outputs"]["di"]["path"]).mono()
            described[name] = {"path": record["outputs"]["di"]["path"],
                               "sha256": record["outputs"]["di"]["sha256"]}
    if len(dis) < 2:
        die("give at least two passages (--di, --development-dis)")

    started = time.time()
    pairs = pairs_question(records, args.loss_profile) if records else []

    space = space_module.build(args.pack, amp=amp)
    dimensions = {dimension.path: dimension for dimension in space.dimensions}
    steps = STEPS[(args.pack, amp)]
    renderer = _renderer(args.renderer, args.pack)
    printed, tracks, repeats = {}, [], {}
    try:
        metadata = renderer.metadata()
        topology = signal_benchmark.fixed_topology(space, amp, None,
                                                   renderer.parameter_specs())
        scorer = search.Evaluator(renderer, None, next(iter(dis.values())), space,
                                  profile=args.loss_profile)
        for index, (label, changes) in enumerate(steps):
            values = dict(topology["seed"])
            for path, value in changes.items():
                dimension = dimensions[path]
                values[(dimension.module, dimension.key)] = value
            row = {"step": label, "settings": changes}
            for name, di in dis.items():
                rendered = renderer.render(di, scorer._settings(values))
                printed[(index, name)], row[name] = measure(
                    rendered.audio, rendered.metadata.sample_rate)
                if index == REFERENCE_STEP:
                    again = renderer.render(di, scorer._settings(values))
                    repeat, _ = measure(again.audio, again.metadata.sample_rate)
                    repeats[name] = compare(printed[(index, name)], repeat,
                                            profile=args.loss_profile
                                            ).values.get("harmonic")
            tracks.append(row)
            print(f"  {label}", file=sys.stderr, flush=True)
    finally:
        close = getattr(renderer, "close", None)
        if close is not None:
            close()

    def harmonic(a, b):
        return compare(printed[a], printed[b],
                       profile=args.loss_profile).values.get("harmonic")

    names = list(dis)
    setting_effect = {}
    for index, (label, _) in enumerate(steps):
        if index == REFERENCE_STEP:
            continue
        setting_effect[label] = [harmonic((index, n), (REFERENCE_STEP, n)) for n in names]
    passage_effect = {label: [harmonic((index, a), (index, b))
                              for a, b in itertools.combinations(names, 2)]
                      for index, (label, _) in enumerate(steps)}
    note_kept = {label: sum(same_note(tracks[index][n]["note"],
                                      tracks[REFERENCE_STEP][n]["note"]) for n in names)
                 for index, (label, _) in enumerate(steps) if index != REFERENCE_STEP}

    def summary(values):
        present = [v for v in values if v is not None]
        if not present:
            return {"n": 0, "of": len(values)}
        return {"n": len(present), "of": len(values),
                "median": round(statistics.median(present), 3),
                "p90": round(float(np.percentile(present, 90)), 3),
                "max": round(max(present), 3)}

    rescored = [rescore(path, args.loss_profile) for path in args.recordings]
    elapsed = time.time() - started

    print(f"\n{args.pack}/{amp}, {metadata.renderer_id} {metadata.plugin_version}, "
          f"{len(names)} passages, {elapsed:.0f}s")
    if pairs:
        kept = sum(row["same_note"] for row in pairs)
        edges = sum(bool(row[side]["note"] and row[side]["note"]["at_edge"])
                    for row in pairs for side in ("di", "amp"))
        print(f"pairs: DI and amp track measured on the same note in {kept} of "
              f"{len(pairs)} takes; {edges} of {2 * len(pairs)} pitches at a range edge")
        for row in pairs:
            d, a = row["di"]["note"], row["amp"]["note"]
            print(f"  {row['part'][:40]:40} DI {d and d['f0_hz']} Hz, amp "
                  f"{a and a['f0_hz']} Hz, harmonic {row['harmonic']}")
    print(f"repeat (same render twice, middle step): {summary(list(repeats.values()))}")
    print("setting effect (step against the middle step, same passage):")
    for label, values in setting_effect.items():
        print(f"  {label:24} {summary(values)}; same note {note_kept[label]}/{len(names)}")
    print("passage effect (two passages, same step):")
    for label, values in passage_effect.items():
        print(f"  {label:24} {summary(values)}")
    for document in rescored:
        print(f"rescored {document['path']}:")
        for row in document["rows"]:
            cells = "  ".join(
                f"{key.replace('_', ' ')} {row[key]['closer']}/{row[key]['of']} "
                f"{row[key]['mean_change']:+.0%} p={row[key]['p']:.3f}"
                for key in ("with_harmonic", "without_harmonic",
                            "without_harmonic_or_level"))
            print(f"  {row['a']} vs {row['b']}: {cells}")
    caveat = _backend_caveat(metadata)
    if caveat:
        print(f"\n  {caveat}.")

    if args.json:
        args.json.write_text(json.dumps({
            "schema": SCHEMA, "source_commit": commit,
            "command": " ".join(shlex.quote(arg) for arg in sys.argv),
            "elapsed_s": round(elapsed, 1), "pack": args.pack, "amp": amp,
            "loss_profile": args.loss_profile, "dis": described,
            "backend": metadata.as_dict(), "measurement_caveat": caveat or None,
            "pairs": pairs, "tracks": tracks, "repeats": repeats,
            "setting_effect": {k: summary(v) for k, v in setting_effect.items()},
            "passage_effect": {k: summary(v) for k, v in passage_effect.items()},
            "note_kept": note_kept, "rescored": rescored,
        }, indent=1) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    guarded(main)
