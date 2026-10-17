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
import math
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from _cli import add_data_dir_arg, die, guarded  # noqa: E402
from packs import paths  # noqa: E402

SCHEMA = "arrangement-1"
CONFIDENCE = ("documented", "corroborated", "inferred", "unknown")
# Seconds come only from the user or a source timed against the same recording; a
# guess at seconds would read as timing to the side that aligns sections to audio.
TIMED_BY = ("user", "source timestamp")
TIME_BASIS = TIMED_BY + ("unknown",)
SOURCE_KINDS = ("rig rundown", "interview", "lesson", "tab", "forum", "article",
                "liner notes", "video", "other")
PAN = ("L", "R", "C", None)
# Every key is required, null where unknown, so a reader never meets a missing key.
TOP_KEYS = ("schema", "song", "guitars", "sections", "changes", "sources", "gaps")
SONG_KEYS = ("artist", "title", "recording", "duration_s")
GUITAR_KEYS = ("id", "player", "instrument", "rig", "role", "pan", "doubled", "tuning",
               "capo", "confidence", "sources")
SECTION_KEYS = ("name", "order", "start_s", "end_s", "time_basis", "guitars",
                "confidence", "sources")
CHANGE_KEYS = ("guitar", "at_section", "at_s", "time_basis", "what", "confidence",
               "sources")
SOURCE_KEYS = ("id", "url", "kind", "note")


def slug(artist: str, title: str) -> str:
    """`Eagles`, `Hotel California` -> `eagles-hotel-california`; accents folded
    (`Sigur Rós` -> `sigur-ros`). A name with no Latin letters at all (`椎名林檎`) gets
    a short hash of the text instead, so two such songs never share a file."""
    import hashlib
    import unicodedata

    text = f"{artist} {title}"
    folded = "".join(c for c in unicodedata.normalize("NFKD", text)
                     if not unicodedata.combining(c)).lower()
    found = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    if len(re.sub(r"[^a-z]", "", found)) < 2:
        found = "song-" + hashlib.sha256(text.encode()).hexdigest()[:12]
    return found


def location(artist: str, title: str) -> pathlib.Path:
    return paths.data_root() / "research" / slug(artist, title) / "arrangement.json"


def _number(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def problems(doc) -> list:
    """Every way `doc` departs from arrangement-1, as sentences; empty when none."""
    found = []
    if not isinstance(doc, dict):
        return ["the file is not a JSON object"]

    def keys(item, required, where) -> bool:
        if not isinstance(item, dict):
            found.append(f"{where} is not an object")
            return False
        missing = [k for k in required if k not in item]
        if missing:
            found.append(f"{where} lacks {', '.join(missing)} (use null when unknown)")
        return True

    def listed(value, where) -> list:
        if not isinstance(value, list):
            found.append(f"{where} must be a list")
            return []
        return value

    keys(doc, TOP_KEYS, "the file")
    if doc.get("schema") != SCHEMA:
        found.append(f"schema is {doc.get('schema')!r}, expected {SCHEMA!r}")

    song, duration = doc.get("song"), None
    if keys(song, SONG_KEYS, "song"):
        for key in ("artist", "title", "recording"):
            if not _text(song.get(key)):
                found.append(f"song.{key} must be a non-empty string")
        duration = song.get("duration_s")
        if duration is not None and not (_number(duration) and duration > 0):
            found.append("song.duration_s must be a positive number or null")
            duration = None

    source_ids = set()
    for i, source in enumerate(listed(doc.get("sources"), "sources")):
        where = f"sources[{i}]"
        if not keys(source, SOURCE_KEYS, where):
            continue
        sid = source.get("id")
        if not _text(sid):
            found.append(f"{where}.id must be a non-empty string")
        elif sid in source_ids:
            found.append(f"{where}.id {sid!r} is used twice")
        else:
            source_ids.add(sid)
        url = source.get("url")
        if not (isinstance(url, str) and re.match(r"https?://[^/\s]+\.[^/\s]+", url)):
            found.append(f"{where}.url must be a web address")
        if source.get("kind") not in SOURCE_KINDS:
            found.append(f"{where}.kind must be one of {', '.join(SOURCE_KINDS)}")

    def cited(item, where):
        """Confidence and sources: documented cites a source, corroborated two, and
        every cited id exists."""
        confidence = item.get("confidence")
        if confidence not in CONFIDENCE:
            found.append(f"{where}.confidence must be one of {', '.join(CONFIDENCE)}")
        cites = listed(item.get("sources"), f"{where}.sources")
        for sid in cites:
            if not isinstance(sid, str) or sid not in source_ids:
                found.append(f"{where}.sources names {sid!r}, which is not in sources")
        named = {sid for sid in cites if isinstance(sid, str)}
        if confidence == "documented" and not named:
            found.append(f"{where} is documented but cites no source")
        if confidence == "corroborated" and len(named) < 2:
            found.append(f"{where} is corroborated but cites fewer than two sources")

    guitar_ids = set()
    guitars = listed(doc.get("guitars"), "guitars")
    if isinstance(doc.get("guitars"), list) and not guitars:
        found.append("guitars must name at least one guitar")
    for i, guitar in enumerate(guitars):
        where = f"guitars[{i}]"
        if not keys(guitar, GUITAR_KEYS, where):
            continue
        gid = guitar.get("id")
        if not _text(gid):
            found.append(f"{where}.id must be a non-empty string")
        elif gid in guitar_ids:
            found.append(f"{where}.id {gid!r} is used twice")
        else:
            guitar_ids.add(gid)
        for key in ("instrument", "role"):
            if not _text(guitar.get(key)):
                found.append(f"{where}.{key} must be a non-empty string")
        for key in ("player", "tuning"):
            if guitar.get(key) is not None and not _text(guitar.get(key)):
                found.append(f"{where}.{key} must be a non-empty string or null")
        if guitar.get("pan") not in PAN:
            found.append(f"{where}.pan must be L, R, C or null")
        if not any(guitar.get("doubled") is v for v in (True, False, None)):
            found.append(f"{where}.doubled must be true, false or null (unknown)")
        capo = guitar.get("capo")
        if capo is not None and (not isinstance(capo, int) or isinstance(capo, bool)
                                 or not 0 <= capo <= 24):
            found.append(f"{where}.capo must be a fret number (0-24) or null")
        rig = guitar.get("rig")
        if (not isinstance(rig, dict) or not isinstance(rig.get("effects"), list)
                or not all(_text(e) for e in rig.get("effects"))
                or any(rig.get(k) is not None and not _text(rig.get(k))
                       for k in ("guitar", "amp"))):
            found.append(f"{where}.rig must hold guitar and amp (text or null) and "
                         "effects (a list of text)")
        cited(guitar, where)

    def timed(item, where, at_keys):
        """Seconds only with a basis that can give them; finite, non-negative."""
        basis = item.get("time_basis")
        if basis not in TIME_BASIS:
            found.append(f"{where}.time_basis must be one of {', '.join(TIME_BASIS)}")
        values = [item.get(k) for k in at_keys]
        for key, value in zip(at_keys, values):
            if value is not None and not (_number(value) and value >= 0):
                found.append(f"{where}.{key} must be a non-negative number or null")
        if basis == "unknown" and any(v is not None for v in values):
            found.append(f"{where} gives seconds but its time_basis is unknown: "
                         "seconds come only from the user or a timed source")
        if basis in TIMED_BY and all(v is None for v in values):
            found.append(f"{where} has time_basis {basis!r} but gives no seconds")

    names, orders = {}, []
    for i, section in enumerate(listed(doc.get("sections"), "sections")):
        where = f"sections[{i}]"
        if not keys(section, SECTION_KEYS, where):
            continue
        name = section.get("name")
        if not _text(name):
            found.append(f"{where}.name must be a non-empty string")
        elif name.strip().lower() in names:
            found.append(f"{where}.name {name!r} is used twice; number repeats (chorus 2)")
        else:
            names[name.strip().lower()] = name
        order = section.get("order")
        if not isinstance(order, int) or isinstance(order, bool):
            found.append(f"{where}.order must be an integer")
        else:
            orders.append(order)
        timed(section, where, ("start_s", "end_s"))
        start, end = section.get("start_s"), section.get("end_s")
        if _number(start) and _number(end) and not start < end:
            found.append(f"{where} ends before it starts")
        if _number(end) and duration is not None and end > duration:
            found.append(f"{where} ends after the song does")
        played = section.get("guitars")
        if not isinstance(played, dict):
            found.append(f"{where}.guitars must map guitar ids to what each plays")
        else:
            for gid, what in played.items():
                if gid not in guitar_ids:
                    found.append(f"{where}.guitars names {gid!r}, which is not in guitars")
                if not _text(what):
                    found.append(f"{where}.guitars[{gid!r}] must say what it plays")
        cited(section, where)
    if len(orders) != len(set(orders)):
        found.append("two sections share an order")

    for i, change in enumerate(listed(doc.get("changes"), "changes")):
        where = f"changes[{i}]"
        if not keys(change, CHANGE_KEYS, where):
            continue
        guitar = change.get("guitar")
        if not isinstance(guitar, str) or guitar not in guitar_ids:
            found.append(f"{where}.guitar must be one of the guitars' ids")
        at = change.get("at_section")
        if at is not None and not (isinstance(at, str) and at.strip().lower() in names):
            found.append(f"{where}.at_section {at!r} is not a section name")
        timed(change, where, ("at_s",))
        if at is None and change.get("at_s") is None:
            found.append(f"{where} says neither which section nor when")
        if not _text(change.get("what")):
            found.append(f"{where}.what must say what changes")
        cited(change, where)

    gaps = doc.get("gaps")
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
