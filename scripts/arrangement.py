#!/usr/bin/env python3
"""Where a song's arrangement prior goes, and whether one is well formed.

    python scripts/arrangement.py path "Eagles" "Hotel California"
    python scripts/arrangement.py check ARRANGEMENT.json

An arrangement prior records what research found about a song's guitars: how many,
of what kind, which sections each plays, and the sound changes between sections,
each item with its sources and a confidence. `generate` writes one when it
researches a real song; the ML side aligns its section names and order to the audio
and checks it there, never trusting it blindly. The format is
`reference/arrangement.md`.

`path` prints where the file belongs under the data root
(`research/<artist>-<title>/arrangement.json`) and creates nothing. `check` reads a
file and reports every problem it finds, or a one-line summary when there are none.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from _cli import add_data_dir_arg, die, guarded  # noqa: E402
from packs import paths  # noqa: E402

SCHEMA = "arrangement-1"
CONFIDENCE = ("documented", "corroborated", "inferred", "unknown")
TIME_BASIS = ("user", "source timestamp", "estimated from song structure", "unknown")
SOURCE_KINDS = ("rig rundown", "interview", "lesson", "tab", "forum", "article",
                "liner notes", "video", "other")
PAN = ("L", "R", "C", None)


def slug(artist: str, title: str) -> str:
    """`Eagles`, `Hotel California` -> `eagles-hotel-california`."""
    text = f"{artist} {title}".lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def location(artist: str, title: str) -> pathlib.Path:
    return paths.data_root() / "research" / slug(artist, title) / "arrangement.json"


def _number_or_none(value) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


def problems(doc) -> list:
    """Every way `doc` departs from arrangement-1, as sentences; empty when none."""
    found = []
    if not isinstance(doc, dict):
        return ["the file is not a JSON object"]
    if doc.get("schema") != SCHEMA:
        found.append(f"schema is {doc.get('schema')!r}, expected {SCHEMA!r}")

    song = doc.get("song")
    if not isinstance(song, dict):
        found.append("song is missing")
    else:
        for key in ("artist", "title", "recording"):
            if not isinstance(song.get(key), str) or not song.get(key).strip():
                found.append(f"song.{key} must be a non-empty string")
        duration = song.get("duration_s")
        if not _number_or_none(duration) or (duration is not None and duration <= 0):
            found.append("song.duration_s must be a positive number or null")

    sources = doc.get("sources")
    source_ids = set()
    if not isinstance(sources, list):
        found.append("sources must be a list")
        sources = []
    for i, source in enumerate(sources):
        where = f"sources[{i}]"
        if not isinstance(source, dict):
            found.append(f"{where} is not an object")
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid:
            found.append(f"{where}.id must be a non-empty string")
        elif sid in source_ids:
            found.append(f"{where}.id {sid!r} is used twice")
        else:
            source_ids.add(sid)
        if not str(source.get("url", "")).startswith(("http://", "https://")):
            found.append(f"{where}.url must be a web address")
        if source.get("kind") not in SOURCE_KINDS:
            found.append(f"{where}.kind must be one of {', '.join(SOURCE_KINDS)}")

    def cited(item, where):
        """The confidence and sources of one item: documented needs a source,
        corroborated two, and every cited id must exist."""
        confidence = item.get("confidence")
        cites = item.get("sources", [])
        if confidence not in CONFIDENCE:
            found.append(f"{where}.confidence must be one of {', '.join(CONFIDENCE)}")
        if not isinstance(cites, list):
            found.append(f"{where}.sources must be a list of source ids")
            return
        for sid in cites:
            if sid not in source_ids:
                found.append(f"{where}.sources names {sid!r}, which is not in sources")
        if confidence == "documented" and len(cites) < 1:
            found.append(f"{where} is documented but cites no source")
        if confidence == "corroborated" and len(set(cites)) < 2:
            found.append(f"{where} is corroborated but cites fewer than two sources")

    guitars = doc.get("guitars")
    guitar_ids = set()
    if not isinstance(guitars, list) or not guitars:
        found.append("guitars must be a non-empty list")
        guitars = []
    for i, guitar in enumerate(guitars):
        where = f"guitars[{i}]"
        if not isinstance(guitar, dict):
            found.append(f"{where} is not an object")
            continue
        gid = guitar.get("id")
        if not isinstance(gid, str) or not gid:
            found.append(f"{where}.id must be a non-empty string")
        elif gid in guitar_ids:
            found.append(f"{where}.id {gid!r} is used twice")
        else:
            guitar_ids.add(gid)
        for key in ("instrument", "role"):
            if not isinstance(guitar.get(key), str) or not guitar.get(key).strip():
                found.append(f"{where}.{key} must be a non-empty string")
        if guitar.get("pan") not in PAN:
            found.append(f"{where}.pan must be L, R, C or null")
        if guitar.get("doubled") not in (True, False, None):
            found.append(f"{where}.doubled must be true, false or null (unknown)")
        if guitar.get("tuning") is not None and not isinstance(guitar.get("tuning"), str):
            found.append(f"{where}.tuning must be a string or null")
        capo = guitar.get("capo")
        if capo is not None and (not isinstance(capo, int) or isinstance(capo, bool)
                                 or not 0 <= capo <= 24):
            found.append(f"{where}.capo must be a fret number (0-24) or null")
        rig = guitar.get("rig", {})
        if not isinstance(rig, dict) or not isinstance(rig.get("effects", []), list):
            found.append(f"{where}.rig must be an object whose effects is a list")
        cited(guitar, where)

    sections = doc.get("sections", [])
    names, orders = set(), []
    if not isinstance(sections, list):
        found.append("sections must be a list")
        sections = []
    for i, section in enumerate(sections):
        where = f"sections[{i}]"
        if not isinstance(section, dict):
            found.append(f"{where} is not an object")
            continue
        name = section.get("name")
        if not isinstance(name, str) or not name.strip():
            found.append(f"{where}.name must be a non-empty string")
        elif name in names:
            found.append(f"{where}.name {name!r} is used twice; number repeats (chorus 2)")
        else:
            names.add(name)
        order = section.get("order")
        if not isinstance(order, int) or isinstance(order, bool):
            found.append(f"{where}.order must be an integer")
        else:
            orders.append(order)
        start, end = section.get("start_s"), section.get("end_s")
        if not (_number_or_none(start) and _number_or_none(end)):
            found.append(f"{where}.start_s and end_s must be numbers or null")
        elif start is not None and end is not None and not 0 <= start < end:
            found.append(f"{where} ends before it starts")
        if section.get("time_basis") not in TIME_BASIS:
            found.append(f"{where}.time_basis must be one of {', '.join(TIME_BASIS)}")
        elif start is not None and section.get("time_basis") == "unknown":
            found.append(f"{where} has a start_s but its time_basis is unknown")
        played = section.get("guitars", {})
        if not isinstance(played, dict):
            found.append(f"{where}.guitars must map guitar ids to what each plays")
        else:
            for gid in played:
                if gid not in guitar_ids:
                    found.append(f"{where}.guitars names {gid!r}, which is not in guitars")
        cited(section, where)
    if len(orders) != len(set(orders)):
        found.append("two sections share an order")

    for i, change in enumerate(doc.get("changes", [])):
        where = f"changes[{i}]"
        if not isinstance(change, dict):
            found.append(f"{where} is not an object")
            continue
        if change.get("guitar") not in guitar_ids:
            found.append(f"{where}.guitar must be one of the guitars' ids")
        at = change.get("at_section")
        if at is not None and at not in names:
            found.append(f"{where}.at_section {at!r} is not a section name")
        if not _number_or_none(change.get("at_s")):
            found.append(f"{where}.at_s must be a number or null")
        if at is None and change.get("at_s") is None:
            found.append(f"{where} says neither which section nor when")
        if not isinstance(change.get("what"), str) or not change.get("what").strip():
            found.append(f"{where}.what must say what changes")
        cited(change, where)

    gaps = doc.get("gaps", [])
    if not isinstance(gaps, list) or not all(isinstance(g, str) for g in gaps):
        found.append("gaps must be a list of sentences")
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_data_dir_arg(ap)
    sub = ap.add_subparsers(dest="command", required=True)
    where = sub.add_parser("path", help="print where a song's arrangement prior belongs")
    where.add_argument("artist")
    where.add_argument("title")
    check = sub.add_parser("check", help="report what is wrong with an arrangement prior")
    check.add_argument("file", type=pathlib.Path)
    args = ap.parse_args()

    if args.command == "path":
        paths.set_data_root(args.data_dir)
        print(location(args.artist, args.title))
        return
    doc = json.loads(args.file.read_text())
    found = problems(doc)
    if found:
        die(f"{args.file} is not a valid {SCHEMA} prior:\n  " + "\n  ".join(found))
    song = doc["song"]
    print(f"ok: {song['artist']} - {song['title']} ({song['recording']}): "
          f"{len(doc['guitars'])} guitar(s), {len(doc.get('sections', []))} section(s), "
          f"{len(doc.get('changes', []))} change(s), {len(doc['sources'])} source(s)")


if __name__ == "__main__":
    guarded(main)
