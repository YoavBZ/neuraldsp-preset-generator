"""The generate routing and research-edits check (docs/generate-routing-plan.md).

    parts     write docs/generate-routing-parts.json: the development parts, each once,
              with a neutral description and the excerpt, before any agent runs.

Development parts only. Every part is checked against the split it was declared in;
nothing held-out is opened.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DIREC = pathlib.Path.home() / "ndsp-presets" / "learn" / "direc"
SOURCES = (DIREC / "rescore" / "distances.json", DIREC / "songs-check" / "distances.json")
PARTS = ROOT / "docs" / "generate-routing-parts.json"
AMPS = ("pr12", "sw50r", "ac20")
BASELINES = {
    "clean": json.loads((ROOT / "docs/clean-baseline-choice.json").read_text())["presets"],
    "crunch": json.loads((ROOT / "docs/crunch-baseline-choice.json").read_text())["presets"],
    "heavier": {"pr12": "factory:Neural DSP/Vintage Metal",
                "sw50r": "factory:Artists/Royce Whittaker/Wall Of Doom",
                "ac20": "factory:Artists/Charlie Robbins/Dirty Coil Rhythm"},
}


def scored(entry) -> bool:
    """All nine starting presets on both halves of the flat measfix judge."""
    for amp in AMPS:
        for half in ("A", "B"):
            row = entry.get(f"flat|{amp}|measfix_{half}") or {}
            if any(BASELINES[c][amp] not in row for c in BASELINES):
                return False
    return True


def crop_dirs():
    """slug -> (crop folder, label, label source, band, set) for development parts."""
    from learn import set3
    from learn import songs_check as SC
    crops3 = pathlib.Path.home() / "ndsp-presets" / "references" / "validation-crops-set3"

    out = {}
    for p in set3.parts("development"):
        out[p["slug"]] = (crops3 / p["slug"], p["gain_class"], "set-3 catalogue",
                          p["band"], 3)
    for slug, p in SC.parts().items():
        if p["set"] == 12:
            out[slug] = (p["crop"], p["gain_class"], "gain classifier (prep-sets12.json)",
                         p["band"], 12)
    return out


def build_parts():
    entries = {}
    for source in SOURCES:
        for slug, entry in json.loads(source.read_text()).items():
            entries.setdefault(slug, entry)          # set-3 parts in both are identical
    known = crop_dirs()
    rows, dropped = [], []
    for slug in sorted(entries):
        if slug not in known:
            dropped.append((slug, "not a known development part"))
            continue
        if not scored(entries[slug]):
            dropped.append((slug, "not all nine starting presets scored on both halves"))
            continue
        crop, label, label_source, band, set_id = known[slug]
        record = json.loads((pathlib.Path(crop) / "record.json").read_text())
        # Set 3's crops record no split; its declaration (`set3.parts("development")`,
        # which `crop_dirs` reads) is what makes them development.
        if set_id == 12 and record.get("split") != "development":
            raise SystemExit(f"{slug}: split {record.get('split')!r}, refusing")
        rows.append(dict(slug=slug, song=record.get("song"), part=record.get("part"),
                         source=record.get("source"), band=band, set=set_id,
                         label=label, label_source=label_source,
                         start_s=record["excerpt_start_s"],
                         duration_s=record["excerpt_duration_s"],
                         crop=str(crop)))
    # Parts of one song whose excerpts overlap play at the same time: a time range alone
    # cannot say which guitar is meant, so they are unroutable from the input (plan R7).
    by_song = {}
    for row in rows:
        by_song.setdefault((row["source"], row["song"]), []).append(row)
    for group in by_song.values():
        for row in group:
            others = [o for o in group if o is not row
                      and o["start_s"] < row["start_s"] + row["duration_s"]
                      and row["start_s"] < o["start_s"] + o["duration_s"]]
            row["overlaps"] = [o["slug"] for o in others]
            row["routable"] = not any(o["label"] != row["label"] for o in others)
            row["description"] = (
                f"the electric guitar in the excerpt starting at "
                f"{int(row['start_s'] // 60)}:{row['start_s'] % 60:04.1f}, "
                f"{row['duration_s']:.0f} s long")
    return rows, dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["parts"])
    args = ap.parse_args()
    if args.step == "parts":
        if PARTS.exists():
            raise SystemExit(f"{PARTS} exists; the part list is written once")
        rows, dropped = build_parts()
        PARTS.write_text(json.dumps({"plan": "docs/generate-routing-plan.md",
                                     "parts": rows, "dropped": dropped}, indent=1) + "\n")
        classes = {}
        for row in rows:
            classes[row["label"]] = classes.get(row["label"], 0) + 1
        print(f"{len(rows)} parts in {len({(r['source'], r['song']) for r in rows})} songs; "
              f"{classes}; unroutable {sum(not r['routable'] for r in rows)}; "
              f"dropped {len(dropped)}")


if __name__ == "__main__":
    main()
