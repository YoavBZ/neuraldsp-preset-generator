"""The clean/crunch-led pool's step 2 groundwork (`docs/clean-crunch-pool-plan.md`, approved by the user on 2026-10-28,
"Yes for all"): the released sessions, the pool's band guards, the released sessions' DI inventory, sections, backing
metadata and stem scan. Zero renders, no training, no separation.

    $MAIN -m learn.cc_pool inventory                 # the released sessions' DI rows (no verdicts: those are the ear's)
    $MAIN -m learn.cc_pool screen --shard k/3        # part A's screen on them (sections: activity and screens)
    $MAIN -m learn.cc_pool manifest                  # their sections, as part A's manifest rows
    $MAIN -m learn.cc_pool backing                   # per DI: the backing tracks with and without vocals
    $MAIN -m learn.cc_pool stem-scan --shard k/3     # T0's session-level stem scan -> t0/ccstems-<k>of<n>.json
    $MAIN -m learn.cc_pool stems-report              # stems kept and dropped at T0's floor, per session

19 held-out sessions are released into training: 13 by decision B (sets 1-2's 6 held-out Cambridge sessions, set 3's
Dunning Kruger x3 and Silona, set 5's Hazael x2 and Peter White) and 6 by decision C (set 5's re-downloaded backings).
A released session is never a test again (`refuse_test`; `set3.parts`, `set5.parts` and `set5_test.parts` leave it out
unless a reproduction opts in), and neither is its band's other material: Fytakyte "Too Much" (set 5's re-host of BKS's
song) is spent with it, though it stays out of training (`TEST_SPENT`). The released sessions' crops stay held out of
training. Every pool row goes through `pool_rows`: never a V-real band, any of its songs (`VREAL_BANDS`, frozen at
T3's plan step), a known-answer or a reserved band (`refuse_pool_band`).

Outputs: ~/ndsp-presets/learn/clean-crunch-pool/ (part A's own inventory, screen and manifest are never rewritten:
part C's pool checks their hashes) and T0's root, under a prefix of its own (`ccstems`), so T0's `stems` shards and
floor stay as T2 and T3 read them.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
REFS = HOME / "references"
OUT = HOME / "learn/clean-crunch-pool"
PLAN = "docs/clean-crunch-pool-plan.md"
LEDGER_ID = "clean-crunch-pool"
RELEASED_ON = "2026-10-28"
RELEASE_ID = "released-into-training-2026-10-28"     # the declarations' held_out_uses entry
STEM_PREFIX = "ccstems"                              # T0's root: t0/ccstems-<k>of<n>.json (never `stems`)
DISK_GUARD_GB = 31.0

# {session key: (source, band, session dir under REFS, directory holding its tracks under REFS)}: decision B (sets 1-2
# held-out Cambridge, set 3's Dunning Kruger and Silona, set 5's Hazael and Peter White) and C (set 5's re-downloaded
# backings). Bands as the catalogues name them (`clean_di.band_of` for sets 1-2).
RELEASED = {
    "BoogieSnakes_ItsMyRight_Full": ("sets-1-2", "Boogie Snakes", "datasets/cambridge/BoogieSnakes_ItsMyRight_Full",
                                     "datasets/cambridge/BoogieSnakes_ItsMyRight_Full"),
    "Forkupines_Semantics_Full": ("sets-1-2", "Forkupines", "datasets/cambridge/Forkupines_Semantics_Full",
                                  "datasets/cambridge/Forkupines_Semantics_Full"),
    "Forkupines_SugarFaith_Full": ("sets-1-2", "Forkupines", "datasets/cambridge/Forkupines_SugarFaith_Full",
                                   "datasets/cambridge/Forkupines_SugarFaith_Full"),
    "MR0912_NorthToAlaska_Full": ("sets-1-2", "Lights Off Clarity", "datasets/cambridge/MR0912_NorthToAlaska_Full",
                                  "datasets/cambridge/MR0912_NorthToAlaska_Full"),
    "TheMaybeNextYears_OneFlipFlop_Full": ("sets-1-2", "The Maybe Next Years",
                                           "datasets/cambridge/TheMaybeNextYears_OneFlipFlop_Full",
                                           "datasets/cambridge/TheMaybeNextYears_OneFlipFlop_Full"),
    "TimTaler_Stalker_Full": ("sets-1-2", "Tim Taler", "datasets/cambridge/TimTaler_Stalker_Full",
                              "datasets/cambridge/TimTaler_Stalker_Full"),
    "DunningKruger_EnDance_Full": ("set3", "Dunning Kruger", "datasets-set3/cambridge/DunningKruger_EnDance_Full",
                                   "datasets-set3/cambridge/DunningKruger_EnDance_Full/DunningKruger_EnDance_Full"),
    "DunningKruger_JapanSong_Full": ("set3", "Dunning Kruger", "datasets-set3/cambridge/DunningKruger_JapanSong_Full",
                                     "datasets-set3/cambridge/DunningKruger_JapanSong_Full/DunningKruger_JapanSong_Full"),
    "DunningKruger_Sascha_Full": ("set3", "Dunning Kruger", "datasets-set3/cambridge/DunningKruger_Sascha_Full",
                                  "datasets-set3/cambridge/DunningKruger_Sascha_Full/DunningKruger_Sascha_Full"),
    "Silona_LearningHowToFly_Full": ("set3", "Silona", "datasets-set3/cambridge/Silona_LearningHowToFly_Full",
                                     "datasets-set3/cambridge/Silona_LearningHowToFly_Full/Silona_LearningHowToFly_Full"),
    "Hazael_AMiLado_Full": ("set5", "Hazael", "datasets-set5/Hazael - A Mi Lado",
                            "datasets-set5/Hazael - A Mi Lado/Hazael_AMiLado_Full"),
    "Hazael_ResistenciaParaUnNuevoComenzar_Full": (
        "set5", "Hazael", "datasets-set5/Hazael - Resistencia Para Un Nuevo Comenzar",
        "datasets-set5/Hazael - Resistencia Para Un Nuevo Comenzar/Hazael_ResistenciaParaUnNuevoComenzar_Full"),
    "PeterWhite_CrazyGirl_Full": ("set5", "Peter White", "datasets-set5/Peter White - Crazy Girl",
                                  "datasets-set5/Peter White - Crazy Girl/PeterWhite_CrazyGirl_Full"),
    "BKS_TooMuch_Full": ("set5", "BKS", "datasets-set5/BKS - Too Much", "datasets-set5/BKS - Too Much/BKS_TooMuch_Full"),
    "BKS_Bulldozer_Full": ("set5", "BKS", "datasets-set5/BKS - Bulldozer",
                           "datasets-set5/BKS - Bulldozer/BKS_Bulldozer_Full"),
    "RonnieJones_WhyDontYouStay_Full": ("set5", "Ronnie Jones", "datasets-set5/Ronnie Jones - Why Don't You Stay",
                                        "datasets-set5/Ronnie Jones - Why Don't You Stay/RonnieJones_WhyDontYouStay_Full"),
    "SaturnSyndicate_NeverLeaveTheNightAlone_Full": (
        "set5", "Saturn Syndicate", "datasets-set5/Saturn Syndicate - Never Leave The Night Alone",
        "datasets-set5/Saturn Syndicate - Never Leave The Night Alone/SaturnSyndicate_NeverLeaveTheNightAlone_Full"),
    "MR0905_ChrisDurban_Full": ("set5", "Chris Durban", "datasets-set5/Chris Durban - Celebrate",
                                "datasets-set5/Chris Durban - Celebrate/MR0905_ChrisDurban_Full"),
    "HannesKeseberg_YouKnowBetter_Full": ("set5", "Hannes Keseberg", "datasets-set5/Hannes Keseberg - You Know Better",
                                          "datasets-set5/Hannes Keseberg - You Know Better/"
                                          "HannesKeseberg_YouKnowBetter_Full"),
}
# Spent as tests with the release, but not released: set 5's BKS and Fytakyte are one band, and Fytakyte "Too Much" is
# BKS "Too Much" re-hosted (an offset timeline, guitar tracks only). It never trains and is never a test again.
TEST_SPENT = {"Fytakyte": "set 5's re-host of BKS 'Too Much', whose band and song train since 2026-10-28"}
# V-real's 7 bands (T3's frozen V-real-11 membership, `trusted_data_t3.vreal_membership`, by `arm_a_mega53.F_POOL`):
# none of their songs ever enters the pool. `vreal_bands` derives them again from the ledger's frozen list.
VREAL_BANDS = frozenset({"Atlantis Bound", "Zeno", "Diesel13", "Wall Of Death", "Magician's Nephew", "Szymon Skiba",
                         "Eat The Feeder"})
# Other names a released song goes by: Lights Off Clarity's session is "North To Alaska" (its folder and the plan) while
# sets 1-2's catalogue calls the song "All The Same".
SONG_ALIASES = {"MR0912_NorthToAlaska_Full": ("North To Alaska",)}
NOT_ELECTRIC_DI = re.compile(r"(?i)acoustic|midi|synth")   # acoustic DIs, MIDI renders, a guitar synth (BKS Bulldozer)
PART_RE = re.compile(r"(?i)(elecgtr\d+(dt)?|gtr\s*\d*)")   # `clean_di.inventory`'s unpaired-DI part rule
RELEASE_NOTE = f"released into training {RELEASED_ON} ({PLAN}, decision B/C)"


# --- pure: the declaration and the guards ---------------------------------------------------------------------------

def _parts_of(p):
    q = os.path.normpath(os.path.expanduser(os.fspath(p)))
    if not os.path.isabs(q):
        return []
    return [pathlib.PurePosixPath(q).parts, pathlib.PurePosixPath(os.path.realpath(q)).parts]


def released_entry(path, refs=REFS):
    """The released session a file or directory lies under ({key, source, band, dir, tracks}), else None. Absolute (or
    `~`) paths only: a relative path, a band or a crop is never released."""
    for q in _parts_of(path):
        for key, (src, band, sdir, tracks) in RELEASED.items():
            for root in {pathlib.Path(refs).parts, pathlib.Path(os.path.realpath(refs)).parts}:
                r = (*root, *pathlib.PurePosixPath(sdir).parts)
                if q[:len(r)] == r:
                    return {"key": key, "source": src, "band": band, "dir": str(pathlib.Path(refs) / sdir),
                            "tracks": str(pathlib.Path(refs) / tracks)}
    return None


def released_bands():
    return frozenset(b for _, b, _, _ in RELEASED.values())


def band_key(band):
    """A band name compared casefolded, punctuation and spacing ignored ("Magicians Nephew" is "Magician's Nephew")."""
    return re.sub(r"[^0-9a-z]+", "", str(band or "").casefold())


def refuse_pool_band(band):
    """Raise unless `band` may enter the clean/crunch pool: never a V-real band, a known-answer or reserved band, a
    spent-not-released band, or a missing band (fails closed). Names compare by `band_key`."""
    from learn import clean_di as CD

    k = band_key(band)
    if not k:
        raise ValueError("no band: refused (the pool's band guards fail closed)")
    for names, why in ((VREAL_BANDS, "is a V-real band: none of its songs enters the pool"),
                       (CD.KNOWN_ANSWER, "is a known-answer band"), (CD.RESERVED_BANDS, "is a reserved test band"),
                       (TEST_SPENT, "is spent with the release but never trains")):
        if k in {band_key(b) for b in names}:
            raise ValueError(f"{band} {why}")


def check_pool_rows(rows, refuse=None):
    """The pool's guard on DI rows (or examples carrying `band` and `path`): `refuse_pool_band` on every band, then
    part A's held-out refusal (`clean_di.refuse_held_out`, which passes released sessions). Raises on the first
    breach, naming it."""
    from learn import clean_di as CD

    refuse = refuse or CD.refuse_held_out
    for r in rows:
        if not r.get("path"):
            raise ValueError(f"{r.get('id')}: no path (refused)")
        refuse_pool_band(r.get("band"))
        refuse(r)


def pool_rows(*sources, refuse=None):
    """The one way rows enter the clean/crunch pool: every row of every source (the released sessions' inventory,
    tier 1's development rows, part A's inventory rows) through `check_pool_rows`. -> the rows, concatenated, in
    order; a duplicate id refuses."""
    rows = [r for src in sources for r in src]
    ids = [r.get("id") for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate row ids in the pool's sources")
    check_pool_rows(rows, refuse)
    return rows


def name_key(s):
    """A name or path component compared casefolded, with every run of other characters (`_`, `-`, spaces,
    apostrophes) as one '-': "cambridge_It_s_My_Right_Gtr3" and "It's My Right" share "it-s-my-right"."""
    return re.sub(r"[^0-9a-z]+", "-", str(s).casefold()).strip("-")


def released_names(root=PLUGIN_ROOT):
    """The released (and spent) sessions' names in the declarations (docs/), as `name_key`s: session keys, songs,
    part slugs (their crops' folder names) and bands, plus Fytakyte's set-5 session and parts."""
    from learn import clean_di as CD

    out = set(RELEASED) | {f"cambridge/{k}" for k in RELEASED} | set(released_bands()) | set(TEST_SPENT)
    out |= {a for k in RELEASED for a in SONG_ALIASES.get(k, ())}
    v = json.loads((pathlib.Path(root) / "docs/validation-datasets.json").read_text())
    for s in v["sessions"]:
        if pathlib.PurePosixPath(s["path"]).name in RELEASED:
            out |= {s["song"], f"{s['source']}/{s['song']}"}
            out |= {CD.slug12(s["source"], s["song"], p["part"]) for p in s.get("parts", [])}
    for f in ("validation-set3.json", "validation-set5.json"):
        d = json.loads((pathlib.Path(root) / "docs" / f).read_text())
        keys = {s["key"] for s in d["sessions"]
                if s["key"].split("/")[-1] in RELEASED or s["band"] in TEST_SPENT}
        out |= keys | {s["song"] for s in d["sessions"] if s["key"] in keys}
        out |= {p["slug"] for p in [*d["parts"], *d.get("excluded", [])] if p.get("session_key") in keys and p.get("slug")}
    return frozenset(name_key(n) for n in out if name_key(n))


def _released_hit(s, names):
    """The released names a string matches: whole (`name_key`) or as a run of whole tokens inside it."""
    k = name_key(s)
    if not k:
        return []
    if k in names:
        return [k]
    return sorted(n for n in names if f"-{n}-" in f"-{k}-")


def refuse_test(x):
    """Raise if `x` (a band, a session key, a song, a part slug or crop folder, or a path) may not be a test any more:
    a released session, any material of a released band, or material spent with them. Every path component is read,
    casefolded, with `_`, `-` and spaces alike. For any later test's declaration."""
    s = os.fspath(x)
    if released_entry(s) is not None:
        raise ValueError(f"released into training on {RELEASED_ON}: {s!r} is never a test again")
    names = released_names()
    for comp in [s, *pathlib.PurePosixPath(s).parts]:
        hit = _released_hit(comp, names)
        if hit:
            raise ValueError(f"names released or spent material {hit[:3]}: {s!r} is never a test again")


def is_released_part(p):
    """A declared test part (set 3's or set 5's `parts` row) of a released session or a spent band."""
    key = str(p.get("session_key") or "")
    return key.split("/")[-1] in RELEASED or p.get("band") in released_bands() or p.get("band") in TEST_SPENT


def vreal_bands(frozen, f_pool):
    """V-real's bands from its frozen slugs (the ledger's list may carry notes after the slug) and stage F's
    {band: slugs}; a recovered part (not a stage-F slug) by its song's stage-F parts. Fails closed on a slug no band
    holds."""
    def song(s):
        return s.rsplit("-", 1)[0].lower()

    out = set()
    for item in frozen:
        slug = str(item).split(" ")[0]
        bands = [b for b, slugs in f_pool.items() if slug in slugs] or \
                [b for b, slugs in f_pool.items() if any(song(s) == song(slug) for s in slugs)]
        if not bands:
            raise ValueError(f"V-real slug {slug!r}: no stage-F band holds it")
        out |= set(bands)
    return frozenset(out)


def part_of(di):
    m = PART_RE.search(pathlib.PurePosixPath(di).stem)
    return m.group(1) if m else pathlib.PurePosixPath(di).stem


def session_rows(key, tracks_dir, files, band, src, genre, declared, mix=None, vocals=None, excluded=None,
                 status=None):
    """One released session's DI rows, `clean_di.inventory`'s fields. declared: [(part, DI name, [own track names])]
    from the catalogue; a file named as a guitar DI but in no declared part is kept with `clean_di.own_tracks` (name
    rule). Acoustic DIs, MIDI renders and guitar synths are no DI rows, nor is a DI its catalogue excludes
    (`excluded`: {DI name: reasons}; set 5 excludes BKS "Too Much" ElecGtr4a, whose passing amp tracks are
    ElecGtr2's). status: {DI name: note} copied into the row's notes (set 5's part status and reasons). Every row is
    pending: a DI trains only once T0's checks and the ear admit it (the notes carry `clean_di.INTAKE_PENDING`)."""
    from learn import clean_di as CD

    excluded, status = excluded or {}, status or {}
    got = {d for _, d, _ in declared} | set(excluded)
    decl = list(declared) + [(part_of(f), f, None) for f in files if f not in got and CD.is_guitar_di(f)]
    out = []
    for part, di, own in decl:
        if NOT_ELECTRIC_DI.search(di) or di in excluded:
            continue
        if di not in files:
            raise ValueError(f"{key}: declared DI {di} is not on disk")
        r = dict(id=f"{src}/{key}/{di}", path=str(pathlib.Path(tracks_dir) / di), source="cambridge",
                 set=f"released-{RELEASED_ON}", band=band, song=key, part=part, slug=None, gain_class=None,
                 genre=genre, split="library", session_dir=str(tracks_dir),
                 own=[o for o in own if o in files] if own else CD.own_tracks(part, files, di),
                 mix=list(mix) if mix else None, vocals=list(vocals) if vocals else None,
                 notes=[RELEASE_NOTE, *([status[di]] if di in status else []), CD.INTAKE_PENDING])
        r["licence"] = CD.LICENCE["cambridge"]
        r["training_ok"] = False
        out.append(r)
    return out


NOT_OWN_AMP = "passing amp tracks are not its own"     # set 5's reason when a part's amp is another part's


def not_own_amp(p):
    """A set-5 part whose only passing amp tracks belong to another part (BKS "Too Much" ElecGtr4a, "Bulldozer"
    ElecGtr6a): its declared own tracks are wrong, so it is no DI row. Set 5's other exclusions (a modeller reference,
    too few passing windows, a failed waveform test) only weaken the pairing: those DIs stay, pending, reasons noted."""
    return p.get("status") == "excluded" and any(NOT_OWN_AMP in r for r in p.get("reasons") or [])


def backing_candidates(rec, files):
    """(with vocals, without vocals): `pretrain_set.backing_tracks` less every guitar track of the session (other
    guitars' amp and mic tracks, acoustic guitars: `verify_tracks.guitar_sources`)."""
    from learn import pretrain_set as PS
    from learn import verify_tracks as V

    g = set(V.guitar_sources(files))
    withv, nov = PS.backing_tracks(rec, files)
    return [f for f in withv if f not in g], [f for f in nov if f not in g]


def stems_report(row, floor):
    """A scanned session's stems at the floor: (kept by the session-wide rule, dropped, {DI part: kept when only that
    DI's guitar is replaced} by the per-example rule (`verify_tracks.stem_pass_replaced`)."""
    from learn import verify_tracks as V

    stems = row["stems"]
    kept = sorted(f for f, v in stems.items() if v["pass"])
    dropped = sorted(f for f, v in stems.items() if not v["pass"])
    by_part = {}
    for s in row["sources"]:
        k = V.guitar_part_key(s)
        rep = {x for x in row["sources"] if V.guitar_part_key(x) == k}
        by_part[k] = sorted(f for f, v in stems.items() if V.stem_pass_replaced(f, v["takes_db"], floor, rep))
    return kept, dropped, by_part


# --- data: the inventory -------------------------------------------------------------------------------------------

def inventory():
    """Every released session's DI rows (from the catalogues: sets 1-2's in docs, set 3's catalog.json, set 5's
    inventory.json), each refused by the pool's guards like any other row."""
    from learn import clean_di as CD

    rows = []
    v = json.loads(CD.SETS_1_2.read_text())
    s12 = {pathlib.PurePosixPath(s["path"]).name: s for s in v["sessions"]}
    cat3 = json.loads(CD.SET3_CATALOG.read_text())
    c3 = {pathlib.PurePosixPath(s["key"]).name: s for s in cat3["sessions"]}
    inv5 = json.loads((REFS / "datasets-set5/inventory.json").read_text())
    s5 = {s["folder"]: s for s in inv5["sessions"]}
    nm = lambda x: pathlib.PurePosixPath(x).name  # noqa: E731
    for key, (src, band, sdir, tracks) in RELEASED.items():
        tdir = REFS / tracks
        files = sorted(p.name for p in tdir.glob("*.wav"))
        if not files:
            raise SystemExit(f"{key}: no tracks in {tdir}")
        if src == "sets-1-2":
            s = s12[key]
            if s["split"] != "held_out" or CD.band_of(s) != band:
                raise SystemExit(f"{key}: catalogue split {s['split']!r}, band {CD.band_of(s)!r}")
            decl = [(p["part"], p["di"], [p.get("reference"), *p.get("alternate", [])]) for p in s["parts"] if p.get("di")]
            rows += session_rows(key, tdir, files, band, src, s.get("genre"), decl, s.get("mix_tracks"),
                                 s.get("vocal_tracks"))
        elif src == "set3":
            c = c3.get(key)                                  # Sascha: no catalogue session (no paired part)
            if c is not None and c["group"] != band:
                raise SystemExit(f"{key}: catalogue band {c['group']!r}")
            decl = [(p["part"], nm(p["di"]), [nm(p["reference"]), *map(nm, p.get("alternate", []))])
                    for p in (c or {}).get("parts", []) if p.get("di")]
            genre = (c or c3["DunningKruger_EnDance_Full"]).get("genre")
            rows += session_rows(key, tdir, files, band, src, genre, decl,
                                 [nm(m) for m in (c or {}).get("mix_tracks", [])] or None,
                                 [nm(m) for m in (c or {}).get("vocal_tracks", [])] or None)
        else:
            s = s5[pathlib.PurePosixPath(sdir).name]
            if s["band"] != band:
                raise SystemExit(f"{key}: set-5 inventory band {s['band']!r}")
            ps = [p for p in s["parts"] if p.get("di")]
            excl = {nm(p["di"]): p.get("reasons") for p in ps if not_own_amp(p)}
            keep = [p for p in ps if not not_own_amp(p)]
            decl = [(p["part"], nm(p["di"]), [nm(p["reference"]), *map(nm, p.get("alternates", []))])
                    for p in keep if p.get("reference")]
            decl += [(p["part"], nm(p["di"]), None) for p in keep if not p.get("reference")]
            status = {nm(p["di"]): f"set 5's inventory: {p.get('status')}"
                      + (f" ({'; '.join(p['reasons'])})" if p.get("reasons") else "") for p in keep}
            rows += session_rows(key, tdir, files, band, src, s.get("genre_by_library"), decl, excluded=excl,
                                 status=status)
    seen = set()
    for r in rows:
        if r["id"] in seen:
            raise SystemExit(f"duplicate DI row {r['id']}")
        seen.add(r["id"])
    pool_rows(rows)
    return rows


def cross_check(rows, intake):
    """Differences between these rows and step 0's intake rows (released sessions only): ids, paths, parts and own
    tracks. -> [problems]."""
    mine = {r["id"]: r for r in rows}
    theirs = {r["id"]: r for r in intake if r["song"] in RELEASED}
    out = [f"only here: {i}" for i in sorted(set(mine) - set(theirs))]
    out += [f"only in the intake: {i}" for i in sorted(set(theirs) - set(mine))]
    for i in sorted(set(mine) & set(theirs)):
        for k in ("path", "part", "own", "band"):
            if mine[i][k] != theirs[i][k]:
                out.append(f"{i}: {k} {mine[i][k]!r} vs intake {theirs[i][k]!r}")
    return out


# --- commands --------------------------------------------------------------------------------------------------------

def _save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=float))
    tmp.replace(path)


def _load(path):
    return json.loads(path.read_text()) if path.exists() else None


def ledger_ok(path=None):
    """The dev-test ledger holds an entry whose test_id is exactly LEDGER_ID."""
    d = json.loads(pathlib.Path(path or PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    return any(t.get("test_id") == LEDGER_ID for t in d.get("tests", []))


def _inv():
    d = _load(OUT / "inventory.json")
    if d is None:
        raise SystemExit("run `inventory` first")
    pool_rows(d["dis"])
    return d["dis"]


def _guard(swap0):
    from learn import direct_stems as DS

    g = DS._guards("cc-pool", DISK_GUARD_GB, swap0)
    if g:
        print(g[1], flush=True)
        raise SystemExit(g[0])


def cmd_inventory(_):
    import collections

    if not ledger_ok():
        raise SystemExit(f"no ledger entry {LEDGER_ID!r} in docs/dev-test-ledger.json")
    rows = inventory()
    intake = _load(HOME / "learn/trusted-data/intake-2026-10-28/inventory-rows.json")
    probs = cross_check(rows, intake["rows"]) if intake else ["no step 0 intake rows to compare"]
    _save(OUT / "inventory.json", {"plan": PLAN, "released": RELEASED_ON, "dis": rows, "intake_cross_check": probs,
                                   "counts": {"dis": len(rows), "sessions": len({r["song"] for r in rows}),
                                              "by_band": dict(collections.Counter(r["band"] for r in rows))},
                                   "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"{len(rows)} DI rows in {len({r['song'] for r in rows})} sessions; intake cross-check: {probs or 'agrees'}")


def cmd_screen(args):
    from learn import clean_di as CD
    from learn import direct_stems as DS

    rows = _inv()
    sdir = OUT / "screen"
    sdir.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in sdir.glob("*.json") if json.loads(p.read_text()).get("schema") == CD.SCREEN_SCHEMA}
    groups = {}
    for r in rows:
        groups.setdefault(r["session_dir"], []).append(r)
    k, n = args.shard
    jobs = [g for i, g in enumerate(sorted(groups)) if i % n == k]
    swap0 = DS.swap_mb()
    t0 = time.time()
    for i, g in enumerate(jobs):
        _guard(swap0)
        CD.screen_session(groups[g], done, out_dir=sdir)
        print(f"[{i + 1}/{len(jobs)}] {pathlib.Path(g).name} {time.time() - t0:.0f}s", flush=True)
    print(f"SCREEN DONE {k}/{n}")


def cmd_manifest(_):
    import collections

    from learn import clean_di as CD

    rows = _inv()
    screens = {}
    for p in sorted((OUT / "screen").glob("*.json")):
        d = json.loads(p.read_text())
        if d["track"].get("hum_amendment") != CD.HUM_AMENDMENT:             # as part A's `manifest` refuses
            raise SystemExit(f"{p.name} predates part A's amendment 3 (hum rule): screen it again")
        screens[d["path"]] = d
    missing = [r["id"] for r in rows if r["path"] not in screens]
    secs = CD.manifest_rows({"dis": rows}, screens)
    for s in secs:
        s["id"] = f"{s['di']}@{float(s['start_s']):.1f}"
    _save(OUT / "sections.json", {"plan": PLAN, "rule": "part A's manifest rows (activity and screens under "
                                  "amendment 3's hum rule; part A's hum notch was never adopted, so hum-flagged "
                                  "sections stay flagged)", "unscreened": missing, "sections": secs,
                                  "counts": {"sections": len(secs), "clean": sum(s["clean"] for s in secs),
                                             "by_band": dict(collections.Counter(s["band"] for s in secs if s["clean"]))},
                                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"{len(secs)} sections ({sum(s['clean'] for s in secs)} clean) from {len(screens)} screened DIs; "
          f"unscreened {missing}")


def cmd_backing(_):
    from learn import verify_tracks as V

    rows = _inv()
    out = {}
    for r in rows:
        files = sorted(p.name for p in pathlib.Path(r["session_dir"]).glob("*.wav"))
        withv, nov = backing_candidates(r, files)
        out[r["id"]] = {"session_dir": r["session_dir"], "with_vocals": withv, "without_vocals": nov,
                        "has_vocals": len(withv) > len(nov), "mix_list": bool(r.get("mix")),
                        "guitar_tracks": V.guitar_sources(files),
                        "non_musical": [f for f in withv if V.NON_MUSICAL.search(f)]}
    _save(OUT / "backing.json", {"plan": PLAN, "rule": "candidates only: pretrain_set.backing_tracks less every guitar "
                                 "track (verify_tracks.guitar_sources: other guitars' amp and mic tracks, acoustic "
                                 "guitars). An example's stems are `trusted_data.stems_for` under the per-example "
                                 "leak rule on the released sessions' stem scan (`cc_stem_takes`); other guitars "
                                 "enter as renders or rule 1's amp tracks", "dis": out,
                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"backing metadata for {len(out)} DIs")


def cmd_stem_scan(args):
    from learn import direct_stems as DS
    from learn import verify_tracks as V

    if not ledger_ok():
        raise SystemExit(f"no ledger entry {LEDGER_ID!r} in docs/dev-test-ledger.json")
    root = V.OUT
    floor = V.stem_floor(root)
    _, probs = V.load_shards(root, "stems", "sessions", lambda d: d.get("floor_db") == floor)
    if probs:
        raise SystemExit(f"T0's stem scan does not read at this floor ({floor}): {probs}")
    rows = _inv()
    sess = {}
    for r in rows:
        sess.setdefault(r["session_dir"], []).append(r["id"])
    k, n = args.shard
    jobs = [s for i, s in enumerate(sorted(sess)) if i % n == k]
    path = root / "t0" / f"{STEM_PREFIX}-{k}of{n}.json"
    prev = _load(path) or {}
    if prev and prev.get("floor_db") != floor:
        raise SystemExit(f"{path} was scanned at another floor: move it aside by hand")
    done = prev.get("sessions", {})
    swap0 = DS.swap_mb()
    for m, sd in enumerate(jobs):
        if sd in done:
            continue
        _guard(swap0)
        done[sd] = V.scan_session_stems(sd, sess[sd], floor)
        _save(path, {"plan": PLAN, "shard": [k, n], "floor_db": floor, "complete": False, "sessions": done,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        bad = [f for f, v in done[sd]["stems"].items() if not v["pass"]]
        print(f"{m + 1}/{len(jobs)} {pathlib.Path(sd).name}: {len(done[sd]['stems'])} stems, failing {bad} "
              f"({done[sd]['seconds']:.0f} s)", flush=True)
    _save(path, {"plan": PLAN, "shard": [k, n], "floor_db": floor, "complete": all(s in done for s in jobs),
                 "sessions": done, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CC STEM SCAN DONE {k}/{n} (floor {floor:.0f} dB)")


def cc_stem_takes(root=None):
    """The released sessions' stem scan, as `trusted_data.stem_takes` reads T0's: ({session dir: {"sources",
    "stems": {stem: takes_db}}}, floor). Refuses on a missing, incomplete or stale shard."""
    from learn import verify_tracks as V

    root = root or V.OUT
    floor = V.stem_floor(root)
    rows, probs = V.load_shards(root, STEM_PREFIX, "sessions", lambda d: d.get("floor_db") == floor)
    if probs:
        raise SystemExit(f"the released sessions' stem scan cannot be read: {probs}")
    return {sd: {"sources": list(r["sources"]), "stems": {f: v["takes_db"] for f, v in r["stems"].items()}}
            for sd, r in rows.items()}, floor


def cmd_stems_report(_):
    from learn import verify_tracks as V

    root = V.OUT
    floor = V.stem_floor(root)
    rows, probs = V.load_shards(root, STEM_PREFIX, "sessions", lambda d: d.get("floor_db") == floor)
    if probs:
        raise SystemExit(f"cannot read: {probs}")
    rep = {}
    for sd, r in sorted(rows.items()):
        kept, dropped, by_part = stems_report(r, floor)
        rep[pathlib.Path(sd).name] = {"stems": len(r["stems"]), "kept": kept, "dropped": dropped,
                                      "kept_per_example_by_target_part": by_part, "sources": r["sources"]}
        print(f"{pathlib.Path(sd).name}: {len(kept)}/{len(r['stems'])} kept session-wide; dropped {dropped}; "
              f"per-example (target only) kept {[len(v) for v in by_part.values()]}")
    _save(OUT / "stems-report.json", {"floor_db": floor, "sessions": rep, "time": time.strftime("%Y-%m-%d %H:%M:%S")})


def parse_shard(s):
    k, n = (int(x) for x in s.split("/"))
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError("shard k/n with 0 <= k < n")
    return k, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("inventory", cmd_inventory), ("manifest", cmd_manifest), ("backing", cmd_backing),
                     ("stems-report", cmd_stems_report)):
        sub.add_parser(name).set_defaults(fn=fn)
    for name, fn in (("screen", cmd_screen), ("stem-scan", cmd_stem_scan)):
        p = sub.add_parser(name)
        p.add_argument("--shard", type=parse_shard, default=(0, 1))
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
