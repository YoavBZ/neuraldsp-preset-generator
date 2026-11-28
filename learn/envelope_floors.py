"""The spectral-envelope steps' floors (`docs/scratch-envelope-plan.md`, Unit 3; ledger `preset-ladder`
`phase_scratch_envelope`). Row (b)'s stored, hashed answer rendered through each built guitar (`vt-part`, `vt-group`,
`vt-win`, `vt-mag`, `vt-phase`), each in a fresh primed process (2 renders), judged on the held half against the clean
record with the true DI as the judge's DI: 5 x 47 x 2 = 470 renders, plus 8 for this run's own repeat check, 478.

    $MAIN -m learn.envelope_floors floor --shard k/3           # k = 0, 1, 2: one render process each
    $MAIN -m learn.envelope_floors floor --shard k/3 --rerun   # S1: the refused guitars, once more

It runs `voice_floors`' body (`run_floor`) on this run's own world (`EnvelopeWorld`, as `voice_control.ControlWorld`
does): `voice_floors.RealWorld`'s render and judge, this run's guitars (`order`), its stored floors, carry sources and
repeat guitars (`tr-di` and `vc-own`, their floors stored: the exact-notes floors.json and the sound-gap floor
records), and its paths under `PF/fs/envelope/` (`floors/`, `floors-first/`, `repeat/`), so no other run's records are
ever read as this run's. Shard 0 re-renders `tr-di` and `vc-own` on the two check parts first (8 renders): each must
repeat its stored floor exactly, distance and render sha256, or everything stops; the other shards wait for it. A
guitar byte-identical to one already floored carries that floor and names it.

Every command refuses before any render (and before numpy) unless `scratch_envelope.require_envelope` holds with the
build's hash on main (`phase_scratch_envelope_dry`, its proofs held), the stored floors and row (b)'s answers are
main's, and the build and the stored floors cover the draw's parts. Each guitar is loaded by sha256: its file's and
its samples' must be build.json's. The world's pure parts are tested behind fakes in tests/test_envelope_floors.py
(no numpy, no renders).
"""

from __future__ import annotations

import argparse
import pathlib

from learn import scratch_envelope as E
from learn import scratch_exact as SE
from learn import scratch_search as S
from learn import scratch_voice as SV
from learn import voice_floors as VF

PLAN = E.PLAN
MODULE = "learn/envelope_floors.py"
BUILT, STORED = E.BUILT, E.STORED
SHA_FIELDS = ("build", "answers", "floors", "voice_rows", "voice_build")   # the hashed inputs every record names
LABEL = "ENVELOPE FLOORS"


class EnvelopeRuns:
    """This run's guitars and paths as `voice_floors.run_floor` reads them off a world."""

    order = BUILT
    stored_guitars = STORED
    repeat_guitars = STORED
    plan = PLAN
    sha_fields = SHA_FIELDS
    label = LABEL

    @staticmethod
    def floor_path(pk):
        return E.floor_path(pk)

    @staticmethod
    def first_path(pk):
        return E.first_path(pk)

    @staticmethod
    def repeat_path(pk):
        return E.repeat_path(pk)


def require_floors():
    """Every guard, before any render or numpy: the core's guard with the build's hash on main, build.json's proofs
    held, the sound-gap build (vc-own's sha256s), the stored tr-di and vc-own floors (`scratch_envelope.stored_floors`),
    row (b)'s answers, all covering the draw's parts with every built guitar declared. -> the guarded context."""
    m = E.require_envelope(*E.PHASES["floor"])
    build = E.envelope_build(m)
    vbuild = SV._build(m)
    if vbuild.get("proofs_hold") is not True:
        raise SystemExit("the sound-gap build's proofs did not hold")
    ans = S.require_hash(S.phase_answers(SV.STEM_ROW), S.answers_path(SV.STEM_ROW))
    b2 = SE.bank_build(m)
    draw, sd = SE.context()
    keys = sorted(p["pkey"] for p in draw["parts"])
    if (len(keys) != E.PARTS or sorted(build.get("parts") or {}) != keys
            or sorted(vbuild.get("parts") or {}) != keys):
        raise SystemExit("the draw and the two builds do not cover the same parts")
    st, _rows = E.stored_floors(m, keys)
    for k in keys:
        gs = build["parts"][k].get("guitars") or {}
        if any(not (gs.get(g) or {}).get("audio_sha256") or not (gs.get(g) or {}).get("file_sha256") for g in BUILT):
            raise SystemExit(f"{SV.tag(k)}: the envelope build does not declare every guitar's sha256")
        if k not in (ans.get("parts") or {}):
            raise SystemExit(f"{SV.tag(k)}: row (b) has no answer")
    shas = {"build": S.file_sha(E.build_path()), "floors": S.file_sha(SE.floors_path()),
            "answers": S.file_sha(S.answers_path(SV.STEM_ROW)), "voice_rows": S.file_sha(SV.rows_path()),
            "voice_build": S.file_sha(SV.build_path())}
    return {"m": m, "build": build, "voice_build": vbuild, "stored": st, "answers": ans, "b2": b2, "draw": draw,
            "sd": sd, "shas": shas}


class EnvelopeWorld(EnvelopeRuns, VF.RealWorld):
    """This run's renders and files: `voice_floors.RealWorld`'s render and judge, this run's guitars and paths; `tr-di`
    and `vc-own` the stored guitars (`vc-own` loaded by the sound-gap build's sha256s)."""

    def _context(self, pk):
        c = super()._context(pk)
        if E.OWN not in c["stored32"]:
            import numpy as np

            ent = self.ctx["voice_build"]["parts"][pk]["guitars"][E.OWN]
            path = SV.dry_path(E.OWN, pk)
            if not path.exists() or S.file_sha(path) != ent["file_sha256"]:
                raise SystemExit(f"{SV.tag(pk)}: vc-own's file is not the sound-gap build's")
            x32 = np.load(path).astype(np.float32)
            if S.npy_sha(x32) != ent["audio_sha256"]:
                raise SystemExit(f"{SV.tag(pk)}: vc-own's samples are not the sound-gap build's")
            c["stored32"][E.OWN] = x32
        return c

    def dry_shas(self, pk):
        """{guitar: dry sha256}: the built guitars' as the envelope build declares them, tr-di's and vc-own's from their
        audio."""
        c = self._context(pk)
        out = {g: self.ctx["build"]["parts"][pk]["guitars"][g]["audio_sha256"] for g in BUILT}
        out.update({g: S.npy_sha(c["stored32"][g]) for g in STORED})
        return out

    def load(self, pk, g):
        c = self._context(pk)
        if g in STORED:
            return c["stored32"][g]
        import numpy as np

        ent = self.ctx["build"]["parts"][pk]["guitars"][g]
        path = E.dry_path(g, pk)
        if not path.exists() or S.file_sha(path) != ent["file_sha256"]:
            raise SystemExit(f"{SV.tag(pk)}: {g}'s file is not the envelope build's")
        x32 = np.load(path).astype(np.float32)
        if S.npy_sha(x32) != ent["audio_sha256"]:
            raise SystemExit(f"{SV.tag(pk)}: {g}'s samples are not the envelope build's")
        if x32.ndim != 1 or len(x32) != len(c["di32"]):
            raise SystemExit(f"{SV.tag(pk)}: {g} is not the section's length")
        return x32


def open_world():
    return EnvelopeWorld(require_floors())


def cmd_floor(args):
    """The floors of one shard (`voice_floors.run_floor` on `EnvelopeWorld`): the shard checked, every guard before any
    render; shard 0 runs this run's own repeat check (tr-di and vc-own on the two check parts, 8 renders,
    `envelope/repeat/`)."""
    why = VF.shard_refusal(getattr(args, "shard", None))
    if why:
        raise SystemExit(why)
    return VF.run_floor(args, open_world())


COMMANDS = {"floor": cmd_floor}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=S._shard, required=True, help=f"k/{VF.SHARDS}: one render process a shard")
    ap.add_argument("--rerun", action="store_true", help="S1: only the refused guitars, once more")
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
