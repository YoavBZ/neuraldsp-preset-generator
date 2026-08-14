"""Load a plugin pack's manifest and validate human values against it.

The manifest is the *contract*: hand-curated facts about a plugin's parameters
(kind, unit, declared range, enum members). It is committed and shared.

Contrast with the generated observed-value catalog, which is derived from the
user's own presets, stays local, and is only ever advisory — it tells you what
values look *typical*, never what values are *legal*.

    pack = load_pack("morgan")
    spec = pack.get("delay", "delayTime")
    stored = pack.to_stored(spec, 480)      # raises PackError if out of range
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from format.translate import to_binary

PACKS_DIR = pathlib.Path(__file__).parent


class PackError(ValueError):
    """A user-facing problem: unknown parameter, illegal value, missing pack.

    Carries a message meant to be printed as-is, without a traceback.

    A `ValueError` like every other error this repository raises — `SpaceError`,
    `InversionError`, `ChainError`, `ProfileError`, `TimingError`. It was a bare
    `Exception`, and it escapes `match/`: `invert.declared()`, `_validated_amp()`
    and `space.build()` all reach the loader, so `except ValueError` around an
    inversion caught four of the five error types and missed this one.
    """


# Dimensional sanity, by unit. These are NOT the plugin's limits — those are the
# manifest's declared `min`/`max`, which every metered parameter now carries
# (tests/test_pack.py::UNDECLARED_RANGES is empty and guards against that
# changing).
# These reject only values that cannot mean anything in the unit at all: a
# negative tempo, a negative duration, a non-positive frequency. That is a claim
# about arithmetic, not about the plugin, so it can be made without a source.
#
# The floor still earns its place beneath a declared range, because a range can
# be absent on a freshly bootstrapped pack and because it catches nonsense that
# is in range on no plugin at all.
UNIT_FLOOR = {
    "hz": (0.0, False),       # 0 Hz is not a rate or a cutoff
    "bpm": (0.0, False),      # a tempo of zero has no meaning
    "ms": (0.0, True),        # 0 ms is a legitimate "no delay"
    "seconds": (0.0, True),
}


class _Strict(list):
    """A warning sink for callers that passed none: promotes notes to errors.

    Used so a caller who forgets to collect warnings gets told, instead of the
    warning vanishing.
    """

    def append(self, note: str) -> None:  # type: ignore[override]
        raise PackError(note)


@dataclass
class ParamSpec:
    """One parameter's curated facts."""

    module: str
    key: str
    kind: str
    unit: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    range_source: Optional[str] = None
    # Declared for the graphic-EQ bands, whose centres are fixed ISO frequencies.
    # Carried through because a band gain means nothing without the frequency it
    # applies at: it is what the spectral fit in `match/invert.py` solves onto,
    # and what `analysis/refchain.py` places its filters at.
    centre_hz: Optional[float] = None
    members: Optional[Dict[str, str]] = None  # stored int (as str) -> display name
    ui: Optional[str] = None
    note: Optional[str] = None
    writable: bool = True
    # Writable does not imply suitable for tone matching. Utility controls such
    # as pitch transpose must round-trip and remain user-settable, but moving them
    # to imitate the notes in a reference is content matching, not tone matching.
    searchable: bool = True
    # Two different doubts, and they are not interchangeable. `needs_confirmation`
    # says a selector's member names are unknown; `needs_review` says the *kind*
    # is a bootstrap guess, and the kind is what picks the human→stored mapping.
    # A wrong kind is the more expensive of the two: it writes a plausible number
    # instead of failing, so nothing downstream can notice.
    needs_confirmation: bool = False
    needs_review: bool = False
    # Most presets spell switches as "true"/"false". Record-format plugins
    # such as Tone King store the same fact as a binary double, so their
    # writable representation is 1/0. This is storage syntax, not a different
    # human-facing kind.
    switch_encoding: str = "text"

    @property
    def path(self) -> str:
        """Display form. Top-level parameters have no module, so show them bare."""
        return f"{self.module}/{self.key}" if self.module else self.key

    def member_name(self, stored: str) -> Optional[str]:
        """Display name for a stored enum value, if the members are known."""
        if not self.members:
            return None
        try:
            return self.members.get(str(int(float(stored))))
        except (TypeError, ValueError):
            return None


@dataclass
class Pack:
    pack_id: str
    display_name: str
    file_header: str
    parameters: Dict[str, ParamSpec] = field(default_factory=dict)
    # The installed Audio Unit this pack describes, as a type/subtype/manufacturer
    # triple. Only scripts/audit_manifest.py uses it: it re-derives every declared
    # range and selector from the running plugin. Absent on a bootstrapped draft,
    # which is why nothing on the write path may depend on it.
    audio_unit: Dict[str, str] = field(default_factory=dict)
    # Amp display name -> module prefix, so an {amp}-templated recipe can be
    # resolved to the live amp's own EQ module.
    amp_modules: Dict[str, str] = field(default_factory=dict)
    # Optional, declarative signal paths for measurements that need to know how
    # a plugin's controls are wired. Morgan predates this field and can derive
    # its paths from amp_modules; flat-namespace plugins such as Tone King cannot.
    calibration: Dict[str, Any] = field(default_factory=dict)
    # Optional selector conditions for flat namespaces. Maps a parameter path to
    # the selector and members that put that control in circuit; Morgan encodes
    # the same ownership in module prefixes instead.
    search_conditions: Dict[str, Any] = field(default_factory=dict)

    def get(self, module: str, key: str) -> Optional[ParamSpec]:
        return self.parameters.get(f"{module}/{key}")

    def require(self, module: str, key: str) -> ParamSpec:
        spec = self.get(module, key)
        if spec is None:
            raise PackError(
                f"{module}/{key} is not a parameter of {self.display_name}.\n"
                f"  The writer clones a template and mutates existing values; it "
                f"cannot invent new parameter slots.\n"
                f"  Check the spelling against packs/{self.pack_id}/manifest.json."
            )
        return spec

    # -- value translation -------------------------------------------------

    def to_stored(
        self,
        spec: ParamSpec,
        human: Any,
        allow_out_of_range: bool = False,
        warnings: Optional[List[str]] = None,
    ) -> str:
        """Translate a human value to its stored string, validating as we go.

        Raises PackError with an actionable message on anything illegal.

        Non-fatal notes are appended to ``warnings``. Passing no list means "I
        expect no warnings": rather than discard one silently, a note raised
        without somewhere to put it becomes an error. Warnings here flag values
        that may not mean what the caller thinks, so losing one is worse than
        failing.
        """
        notes = warnings if warnings is not None else _Strict()

        if not spec.writable:
            detail = spec.note or (
                "This key is retained only for lossless state round-trip and has "
                "no verified writable Audio Unit control."
                if spec.kind == "internal"
                else ""
            )
            raise PackError(
                f"{spec.path} is marked read-only in the manifest and must not be "
                f"written.\n  {detail}".rstrip()
            )

        # A guessed kind is doubt the manifest already records; until now nothing
        # carried it to the person doing the writing. It warns rather than
        # refuses because a draft pack is meant to be usable while it is being
        # corrected — and because the guess is often right. Checked before the
        # kind branches, since the guess is what chose the branch.
        if spec.needs_review:
            notes.append(
                f"{spec.path} has a guessed kind ({spec.kind}), so {human!r} is "
                f"written through an unverified mapping and may not mean what you "
                f"expect — a metered control guessed as a knob stores 50 as 0.5. "
                f"Compare the result against what the plugin displays, then fix "
                f"`kind` and drop `needs_review` for this parameter in "
                f"packs/{self.pack_id}/manifest.json."
            )

        if spec.kind == "enum":
            if spec.members is None:
                notes.append(
                    f"{spec.path} is a selector whose member names are not known, so "
                    f"{human!r} is written unvalidated and may not mean what you "
                    f"expect. The plugin never displays the stored integer, so run "
                    f"`scripts/probe.py --param {spec.path}` to discover the mapping "
                    f"— or avoid the selector entirely (see this parameter's `note` "
                    f"in packs/{self.pack_id}/manifest.json)."
                )
            return self._enum_to_stored(spec, human)

        if spec.kind == "switch" and spec.members and isinstance(human, str):
            # A switch may declare the plugin's own two labels, and once it does,
            # `member_name` is what show.py and apply_spec.py display — so a
            # reader is shown "Active" and will hand "Active" straight back.
            # Resolve it here; anything unrecognised falls through to the
            # true/false reader, which names the mistake.
            match = _find_member(spec.members, human)
            if match is not None:
                human = match

        try:
            stored = to_binary(spec.kind, human, spec.unit)
            if spec.kind == "switch" and spec.switch_encoding == "numeric":
                stored = "1" if stored == "true" else "0"
        except (ValueError, OverflowError, TypeError) as e:
            if spec.kind == "switch" and spec.members:
                # The error from the true/false reader names only true/false,
                # which is now half the story: this switch also displays its own
                # labels, and those are what a reader was just shown.
                raise PackError(
                    f"{spec.path}: {e}.\n"
                    f"  This switch also accepts its displayed labels: "
                    f"{_render_members(spec.members)}"
                ) from e
            raise PackError(f"{spec.path}: {e}") from e

        self._check_dimensional(spec, stored)
        note = self._check_range(spec, stored, allow_out_of_range)
        if note:
            notes.append(note)
        return stored

    def _check_dimensional(self, spec: ParamSpec, stored: str) -> None:
        """Reject values that cannot mean anything in the parameter's unit.

        Deliberately not overridable by --allow-out-of-range: that flag exists
        for values the plugin might accept but we haven't declared. A negative
        tempo is not in that category — it is nonsense in any plugin.
        """
        floor = UNIT_FLOOR.get(spec.unit or "")
        if floor is None:
            return
        try:
            value = float(stored)
        except ValueError:
            return
        bound, inclusive = floor
        if value > bound or (inclusive and value == bound):
            return
        comparison = "at least" if inclusive else "greater than"
        raise PackError(
            f"{spec.path}: {stored} {spec.unit} is not a possible value — "
            f"{spec.unit} must be {comparison} {_num(bound)}."
        )

    def _enum_to_stored(self, spec: ParamSpec, human: Any) -> str:
        # Accept a member name ("PR12", "Ribbon 121") as well as an integer.
        if isinstance(human, str) and not _is_intish(human):
            if not spec.members:
                raise PackError(
                    f"{spec.path}: cannot resolve the name {human!r} because this "
                    f"selector's members are not yet known.\n"
                    f"  Pass the integer value instead, and consider filling in "
                    f"`members` in packs/{self.pack_id}/manifest.json."
                )
            match = _find_member(spec.members, human)
            if match is None:
                raise PackError(
                    f"{spec.path}: unknown value {human!r}.\n"
                    f"  Valid: {_render_members(spec.members)}"
                )
            return match

        try:
            value = int(round(float(human)))
        except (TypeError, ValueError):
            raise PackError(
                f"{spec.path}: expected an integer selector or a member name, "
                f"got {human!r}."
            ) from None

        if spec.members is not None:
            if str(value) not in spec.members:
                raise PackError(
                    f"{spec.path}: {value} is not a valid selector value.\n"
                    f"  Valid: {_render_members(spec.members)}"
                )
        return str(value)

    def _check_range(self, spec: ParamSpec, stored: str, allow: bool) -> Optional[str]:
        """Return a warning string, raise PackError, or return None if in range."""
        if spec.min is None and spec.max is None:
            return None
        try:
            v = float(stored)
        except ValueError:
            return None
        lo = spec.min if spec.min is not None else float("-inf")
        hi = spec.max if spec.max is not None else float("inf")
        if lo <= v <= hi:
            return None
        unit = f" {spec.unit}" if spec.unit else ""
        message = (
            f"{spec.path}: {stored}{unit} is outside the declared range "
            f"[{_num(lo)}, {_num(hi)}]{unit}"
        )
        if allow:
            return message + " — written anyway (--allow-out-of-range)."
        raise PackError(
            message + ".\n"
            f"  Source: {spec.range_source or 'manifest'}.\n"
            f"  If the plugin really does accept this, widen the range in "
            f"packs/{self.pack_id}/manifest.json; to write it once, pass "
            f"--allow-out-of-range."
        )


def _is_intish(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def _find_member(members: Dict[str, str], name: str) -> Optional[str]:
    target = _norm(name)
    for stored, display in members.items():
        if _norm(display) == target:
            return stored
    return None


def _render_members(members: Dict[str, str]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(members.items(), key=lambda kv: int(kv[0])))


def _num(x: float) -> str:
    if x in (float("inf"), float("-inf")):
        return "unbounded"
    return str(int(x)) if x == int(x) else str(x)


def load_pack(pack_id: str = "morgan") -> Pack:
    """Load a pack manifest by id."""
    path = PACKS_DIR / pack_id / "manifest.json"
    if not path.exists():
        raise PackError(
            f"No pack for {pack_id!r} (looked for {path}).\n"
            f"  Available: {', '.join(list_packs()) or 'none'}"
        )
    raw = json.loads(path.read_text())
    enums = raw.get("enums", {})
    switch_encoding = raw.get("switch_encoding", "text")
    if switch_encoding not in ("text", "numeric"):
        raise PackError(
            f"Pack {pack_id!r} has unknown switch_encoding {switch_encoding!r}; "
            f"expected 'text' or 'numeric'."
        )

    params: Dict[str, ParamSpec] = {}
    for full, entry in raw["parameters"].items():
        module, _, key = full.rpartition("/")
        members = entry.get("members")
        if entry.get("enum"):
            members = enums[entry["enum"]]
        params[full] = ParamSpec(
            module=module,
            key=key,
            kind=entry["kind"],
            unit=entry.get("unit"),
            min=entry.get("min"),
            max=entry.get("max"),
            range_source=entry.get("range_source"),
            centre_hz=entry.get("centre_hz"),
            members=members,
            ui=entry.get("ui"),
            note=entry.get("note"),
            writable=entry.get("writable", True),
            searchable=entry.get("searchable", True),
            needs_confirmation=entry.get("needs_confirmation", False),
            needs_review=entry.get("needs_review", False),
            switch_encoding=entry.get("switch_encoding", switch_encoding),
        )

    return Pack(
        pack_id=raw["pack_id"],
        display_name=raw["display_name"],
        file_header=raw["file_header"],
        parameters=params,
        audio_unit={
            k: v for k, v in raw.get("audio_unit", {}).items() if k != "note"
        },
        amp_modules=raw.get("amp_modules", {}),
        calibration=raw.get("calibration", {}),
        search_conditions=raw.get("search_conditions", {}),
    )


def list_packs() -> List[str]:
    return sorted(p.parent.name for p in PACKS_DIR.glob("*/manifest.json"))


def detect_pack(file_header: str) -> Optional[Pack]:
    """Identify which plugin a preset came from, by its first token.

    Every preset opens with a printable header string naming the plugin
    ("morgan"), which makes it a reliable pack selector for any preset the
    user points at.
    """
    for pack_id in list_packs():
        pack = load_pack(pack_id)
        if pack.file_header == file_header:
            return pack
    return None
