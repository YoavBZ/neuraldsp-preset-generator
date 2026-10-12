"""Set 6's declaration (`docs/validation-set6.md`) and its leakage guard.

Set 6 is MedleyDB (V1 and V2 audio, Zenodo 1649325 and 1715175; CC BY-NC-SA 4.0,
non-commercial research). Every set-6 band is held out: nothing may train, tune or choose
on it before a declared confirmation. The guard fails closed, as sets 4 and 5's do:

    from learn import set6
    set6.is_held_out("Meaxic")                 # True: a band, session key or crop slug
    set6.is_held_out("~/ndsp-presets/references/datasets-medleydb/...")  # True: any path under it
    set6.refuse(path)                          # raises if `path` is set-6 material
    set6.parts(scope="in_scope")               # clean and crunch parts (none: amendment 1)

Anything under the MedleyDB root or the set-6 crop root is held out, listed or not (songs
with no passing pair, single-track songs, metadata, the mixes). `covers` says whether a
name or path is set 6's at all; `learn.set3.is_held_out`, `fold_for_band` and
`training_dis` consult it, so set-6 files cannot reach a training list.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
DECLARATION = PLUGIN_ROOT / "docs" / "validation-set6.json"
REFERENCES = pathlib.Path(os.path.expanduser("~/ndsp-presets/references"))
SET6_ROOT = REFERENCES / "datasets-medleydb"
SET6_CROPS = REFERENCES / "validation-crops-set6"
SCOPES = ("in_scope", "report_only")

# Every MedleyDB song on disk (73, passing or not). Known here as well as from the
# declaration, so the guard fails closed even on a declaration that lags behind; tests
# check that the two agree. session key -> (band, directory under SET6_ROOT). Bands are
# MedleyDB's artist names, with "Music Delta Multitracks" read as "Music Delta" and
# "Sweat" as "SWEAT" (one band each).
SESSIONS = {
    "medleydb/AClassicEducation_NightOwl": ("A Classic Education", "audio/V1/AClassicEducation_NightOwl"),
    "medleydb/AimeeNorwich_Child": ("Aimee Norwich", "audio/V1/AimeeNorwich_Child"),
    "medleydb/AimeeNorwich_Flying": ("Aimee Norwich", "audio/V1/AimeeNorwich_Flying"),
    "medleydb/AlexanderRoss_GoodbyeBolero": ("Alexander Ross", "audio/V1/AlexanderRoss_GoodbyeBolero"),
    "medleydb/AlexanderRoss_VelvetCurtain": ("Alexander Ross", "audio/V1/AlexanderRoss_VelvetCurtain"),
    "medleydb/AmarLal_Rest": ("Amar Lal", "audio/V1/AmarLal_Rest"),
    "medleydb/Auctioneer_OurFutureFaces": ("Auctioneer", "audio/V1/Auctioneer_OurFutureFaces"),
    "medleydb/AvaLuna_Waterduct": ("Ava Luna", "audio/V1/AvaLuna_Waterduct"),
    "medleydb/BigTroubles_Phantom": ("Big Troubles", "audio/V1/BigTroubles_Phantom"),
    "medleydb/CelestialShore_DieForUs": ("Celestial Shore", "audio/V1/CelestialShore_DieForUs"),
    "medleydb/ChrisJacoby_BoothShotLincoln": ("Chris Jacoby", "audio/V1/ChrisJacoby_BoothShotLincoln"),
    "medleydb/ClaraBerryAndWooldog_AirTraffic": ("Clara Berry and Wooldog", "audio/V1/ClaraBerryAndWooldog_AirTraffic"),
    "medleydb/Creepoid_OldTree": ("Creepoid", "audio/V1/Creepoid_OldTree"),
    "medleydb/CroqueMadame_Oil": ("Croque Madame", "audio/V1/CroqueMadame_Oil"),
    "medleydb/CroqueMadame_Pilot": ("Croque Madame", "audio/V1/CroqueMadame_Pilot"),
    "medleydb/EthanHein_GirlOnABridge": ("Ethan Hein", "audio/V1/EthanHein_GirlOnABridge"),
    "medleydb/FacesOnFilm_WaitingForGa": ("Faces on Film", "audio/V1/FacesOnFilm_WaitingForGa"),
    "medleydb/FamilyBand_Again": ("Family Band", "audio/V1/FamilyBand_Again"),
    "medleydb/HopAlong_SisterCities": ("Hop Along", "audio/V1/HopAlong_SisterCities"),
    "medleydb/InvisibleFamiliars_DisturbingWildlife": ("Invisible Familiars", "audio/V1/InvisibleFamiliars_DisturbingWildlife"),
    "medleydb/LizNelson_Rainfall": ("Liz Nelson & Jennifer Davies", "audio/V1/LizNelson_Rainfall"),
    "medleydb/Lushlife_ToynbeeSuite": ("Lushlife", "audio/V1/Lushlife_ToynbeeSuite"),
    "medleydb/Meaxic_TakeAStep": ("Meaxic", "audio/V1/Meaxic_TakeAStep"),
    "medleydb/Meaxic_YouListen": ("Meaxic", "audio/V1/Meaxic_YouListen"),
    "medleydb/MusicDelta_80sRock": ("Music Delta", "audio/V1/MusicDelta_80sRock"),
    "medleydb/MusicDelta_Beatles": ("Music Delta", "audio/V1/MusicDelta_Beatles"),
    "medleydb/MusicDelta_Britpop": ("Music Delta", "audio/V1/MusicDelta_Britpop"),
    "medleydb/MusicDelta_Country2": ("Music Delta", "audio/V1/MusicDelta_Country2"),
    "medleydb/MusicDelta_Disco": ("Music Delta", "audio/V1/MusicDelta_Disco"),
    "medleydb/MusicDelta_Gospel": ("Music Delta", "audio/V1/MusicDelta_Gospel"),
    "medleydb/MusicDelta_Grunge": ("Music Delta", "audio/V1/MusicDelta_Grunge"),
    "medleydb/MusicDelta_Hendrix": ("Music Delta", "audio/V1/MusicDelta_Hendrix"),
    "medleydb/MusicDelta_Punk": ("Music Delta", "audio/V1/MusicDelta_Punk"),
    "medleydb/MusicDelta_Reggae": ("Music Delta", "audio/V1/MusicDelta_Reggae"),
    "medleydb/MusicDelta_Rock": ("Music Delta", "audio/V1/MusicDelta_Rock"),
    "medleydb/MusicDelta_Rockabilly": ("Music Delta", "audio/V1/MusicDelta_Rockabilly"),
    "medleydb/MusicDelta_Shadows": ("Music Delta", "audio/V1/MusicDelta_Shadows"),
    "medleydb/MusicDelta_SpeedMetal": ("Music Delta", "audio/V1/MusicDelta_SpeedMetal"),
    "medleydb/MusicDelta_Zeppelin": ("Music Delta", "audio/V1/MusicDelta_Zeppelin"),
    "medleydb/PortStWillow_StayEven": ("Port St Willow", "audio/V1/PortStWillow_StayEven"),
    "medleydb/PurlingHiss_Lolita": ("Purling Hiss", "audio/V1/PurlingHiss_Lolita"),
    "medleydb/SecretMountains_HighHorse": ("Secret Mountains", "audio/V1/SecretMountains_HighHorse"),
    "medleydb/Snowmine_Curfews": ("Snowmine", "audio/V1/Snowmine_Curfews"),
    "medleydb/StevenClark_Bounty": ("Steven Clark", "audio/V1/StevenClark_Bounty"),
    "medleydb/TablaBreakbeatScience_Animoog": ("Tabla Breakbeat Science", "audio/V1/TablaBreakbeatScience_Animoog"),
    "medleydb/TablaBreakbeatScience_MoodyPlucks": ("Tabla Breakbeat Science", "audio/V1/TablaBreakbeatScience_MoodyPlucks"),
    "medleydb/TablaBreakbeatScience_Vger": ("Tabla Breakbeat Science", "audio/V1/TablaBreakbeatScience_Vger"),
    "medleydb/TheDistricts_Vermont": ("The Districts", "audio/V1/TheDistricts_Vermont"),
    "medleydb/TheScarletBrand_LesFleursDuMal": ("The Scarlet Brand", "audio/V1/TheScarletBrand_LesFleursDuMal"),
    "medleydb/TheSoSoGlos_Emergency": ("The So So Glos", "audio/V1/TheSoSoGlos_Emergency"),
    "medleydb/Cayetana_MissThing": ("Cayetana", "audio/V2/Cayetana_MissThing"),
    "medleydb/DahkaBand_SoldierMan": ("Dahka Band", "audio/V2/DahkaBand_SoldierMan"),
    "medleydb/DeadMilkmen_PrisonersCinema": ("Dead Milkmen", "audio/V2/DeadMilkmen_PrisonersCinema"),
    "medleydb/FilthyBird_IdLikeToKnow": ("Filthy Bird", "audio/V2/FilthyBird_IdLikeToKnow"),
    "medleydb/FruitCathedral_KeepMeRunnin": ("Fruit Cathedral", "audio/V2/FruitCathedral_KeepMeRunnin"),
    "medleydb/LittleTybee_TheAlchemist": ("Little Tybee", "audio/V2/LittleTybee_TheAlchemist"),
    "medleydb/MidnightBlue_HuntingSeason": ("Midnight Blue", "audio/V2/MidnightBlue_HuntingSeason"),
    "medleydb/MidnightBlue_StarsAreScreaming": ("Midnight Blue", "audio/V2/MidnightBlue_StarsAreScreaming"),
    "medleydb/Plasma_GoodShout": ("Plasma", "audio/V2/Plasma_GoodShout"),
    "medleydb/SasquatchConnection_BoomBoxing": ("Sasquatch Connection", "audio/V2/SasquatchConnection_BoomBoxing"),
    "medleydb/SasquatchConnection_HolyClamsBatman": ("Sasquatch Connection", "audio/V2/SasquatchConnection_HolyClamsBatman"),
    "medleydb/SasquatchConnection_Struttin": ("Sasquatch Connection", "audio/V2/SasquatchConnection_Struttin"),
    "medleydb/SasquatchConnection_ThanksALatte": ("Sasquatch Connection", "audio/V2/SasquatchConnection_ThanksALatte"),
    "medleydb/Sweat_AlmostAlways": ("SWEAT", "audio/V2/Sweat_AlmostAlways"),
    "medleydb/Sweat_Anecdoche": ("SWEAT", "audio/V2/Sweat_Anecdoche"),
    "medleydb/Sweat_Elegy": ("SWEAT", "audio/V2/Sweat_Elegy"),
    "medleydb/Sweat_Mesozoic": ("SWEAT", "audio/V2/Sweat_Mesozoic"),
    "medleydb/Sweat_Sn1572": ("SWEAT", "audio/V2/Sweat_Sn1572"),
    "medleydb/Sweat_Tact": ("SWEAT", "audio/V2/Sweat_Tact"),
    "medleydb/TheKitchenettes_Alive": ("The Kitchenettes", "audio/V2/TheKitchenettes_Alive"),
    "medleydb/TheTonTons_Lush": ("The Ton Tons", "audio/V2/TheTonTons_Lush"),
    "medleydb/Torres_NewSkin": ("Torres", "audio/V2/Torres_NewSkin"),
    "medleydb/TrevorAndTheSoundwaves_AloneAndSad": ("Trevor and the Soundwaves", "audio/V2/TrevorAndTheSoundwaves_AloneAndSad"),
}


@functools.lru_cache(maxsize=None)
def _load(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text())


def load(path: pathlib.Path | str = DECLARATION) -> dict:
    """The declaration as written (a cached object: do not modify it)."""
    return _load(str(path))


def parts(path=DECLARATION, scope: str | None = None) -> list[dict]:
    """Kept parts, all held out; `scope` "in_scope" (clean, crunch) or "report_only"
    (high-gain). Reading their audio needs a declared confirmation."""
    if scope is not None and scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}")
    return [p for p in load(path)["parts"] if scope is None or p["scope"] == scope]


def bands(path=DECLARATION) -> list[str]:
    return sorted({s["band"] for s in load(path)["sessions"]})


@functools.lru_cache(maxsize=None)
def _names(path: str = str(DECLARATION)) -> frozenset:
    d = load(path)
    out = set(d["held_out_bands"]) | set(SESSIONS) | {band for band, _ in SESSIONS.values()}
    for s in d["sessions"]:
        out |= {s["band"], s["key"]}
    out |= {p["slug"] for p in [*d["parts"], *d["excluded"]] if p.get("slug")}
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def _relative(path: str = str(DECLARATION)) -> tuple:
    """Session directories as written relative to the set-6 root."""
    dirs = {s["path"] for s in load(path)["sessions"]} | {d for _, d in SESSIONS.values()}
    return tuple(pathlib.PurePosixPath(d).parts for d in sorted(dirs))


def _roots() -> list[tuple]:
    out = set()
    for root in (SET6_ROOT, SET6_CROPS):
        out |= {root.parts, pathlib.Path(os.path.realpath(root)).parts}
    return sorted(out)


def covers(x: str | os.PathLike, path=DECLARATION) -> bool:
    """Whether `x` is set-6 material: a set-6 band, session key or crop slug, or a path
    (absolute, `~`, or relative to the set-6 root) under the set-6 dataset or crop root."""
    s = os.fspath(x)
    if not isinstance(x, os.PathLike) and s in _names(str(path)):
        return True
    q = os.path.normpath(os.path.expanduser(s))
    if os.path.isabs(q):
        cands = {pathlib.PurePosixPath(q).parts, pathlib.PurePosixPath(os.path.realpath(q)).parts}
        return any(c[:len(r)] == r for c in cands for r in _roots())
    rel = pathlib.PurePosixPath(q).parts
    return any(rel[:len(r)] == r for r in _relative(str(path)))


def is_held_out(x: str | os.PathLike, path=DECLARATION) -> bool:
    """True for anything set 6 covers (every set-6 band is held out); KeyError otherwise."""
    if covers(x, path):
        return True
    raise KeyError(f"not a set-6 band, session, crop or path: {os.fspath(x)!r}")


def refuse(x: str | os.PathLike, path=DECLARATION) -> None:
    """Raise ValueError if `x` is set-6 material (for training, tuning or choosing)."""
    if covers(x, path):
        raise ValueError(f"set-6 material is held out (docs/validation-set6.md): {os.fspath(x)!r}")
