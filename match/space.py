"""The set of parameters a search is allowed to move, and what they mean.

Built from a pack manifest, so the space is whatever the plugin actually declares
rather than a list maintained by hand. Three things make it more than a list of
bounds:

**It is conditional.** Morgan carries all three amps in every preset and writing
the inactive one's controls is a silent no-op, so a search that treated all 132
parameters as live would spend most of its budget on controls that do nothing and
then conclude they do nothing. The same applies to every effect behind an
`*Active` switch. `Space.active()` answers which dimensions are live *given the
current values*, and that answer changes as the search flips a switch.

**It refuses what it cannot mean.** Read-only and `internal` parameters, strings,
file paths, selectors whose member names are unknown, and anything whose `kind` is
a bootstrap guess are all left out — the last because a wrong kind writes a
plausible number instead of failing, which is the one error nothing downstream can
notice.

**It speaks human values.** `to_spec()` emits exactly what `apply_spec.py`
consumes, so the winner of a search is written by the same validated path as a
hand-authored preset, and `analysis.refchain` renders from the same dict. Nothing
here writes preset bytes.

Kept stdlib-only at import time, like the rest of the project: numpy is touched
only inside the two vector functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

Key = Tuple[str, str]

# Kinds that cannot be searched over. A `string` is a preset name, a `path` is a
# custom IR on someone's disk, and `internal` is Tone King's read-only state.
UNSEARCHABLE_KINDS = frozenset({"string", "path", "internal"})

# A rotation is a percent and a fraction is 0..1; both are continuous. `metered`
# carries its own declared range in its own unit.
CONTINUOUS_KINDS = frozenset({"rotation", "fraction", "metered"})

# Where a control's stored resolution is finer than anything audible. These are
# engineering choices, not measurements, which is why they are named and gathered
# here rather than buried: a 0.5% step on a knob is already below what the plugin
# displays, and searching finer than that spends budget on numbers nobody can hear.
QUANTA = {
    "rotation": 0.5,      # percent
    "fraction": 0.005,
    "db": 0.25,
    "hz": 1.0,
    "ms": 1.0,
    "bpm": 0.5,
    "seconds": 0.05,
    "semitones": 1.0,
}


class SpaceError(ValueError):
    """A space that cannot be built, or a vector that does not fit it."""


@dataclass(frozen=True)
class Dimension:
    """One thing a search may move, and the condition under which it matters."""

    module: str
    key: str
    kind: str
    unit: Optional[str] = None
    low: Optional[float] = None
    high: Optional[float] = None
    members: Optional[Dict[str, str]] = None
    quantum: Optional[float] = None
    # The switch that has to be on, or the amp that has to be selected, for this
    # dimension to reach the sound at all.
    gate: Optional[Key] = None
    gate_amp: Optional[str] = None

    @property
    def path(self) -> str:
        return f"{self.module}/{self.key}" if self.module else self.key

    @property
    def continuous(self) -> bool:
        return self.kind in CONTINUOUS_KINDS

    @property
    def switch(self) -> bool:
        return self.kind == "switch"

    def clamp(self, value: float) -> float:
        low, high = self.bounds()
        return min(max(float(value), low), high)

    def bounds(self) -> Tuple[float, float]:
        """The searchable range in human units.

        A rotation is a percent and a fraction is 0..1 by definition of the kind;
        a metered control has to have declared a range, and one that has not is
        excluded when the space is built rather than guessed at here.
        """
        if self.kind == "rotation":
            return 0.0, 100.0
        if self.kind == "fraction":
            return 0.0, 1.0
        if self.low is None or self.high is None:
            raise SpaceError(f"{self.path} has no declared range to search over")
        return float(self.low), float(self.high)

    def quantise(self, value: float) -> float:
        if not self.quantum:
            return value
        stepped = round(float(value) / self.quantum) * self.quantum
        # Rounding to a step can leave a long float tail; the spec is read by
        # people as well as by apply_spec.py.
        return round(stepped, 6)


@dataclass
class Space:
    """Every dimension of one pack, plus which of them are live right now."""

    pack_id: str
    dimensions: List[Dimension] = field(default_factory=list)
    amp_modules: Dict[str, str] = field(default_factory=dict)
    # Stored `selectedAmp` integer to module prefix. Separate from `amp_modules`,
    # which is keyed by display name, because a preset holds the integer.
    amp_by_index: Dict[str, str] = field(default_factory=dict)
    excluded: Dict[str, str] = field(default_factory=dict)

    # --- lookups ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.dimensions)

    def by_gate(self, module: str, key: str) -> Dimension:
        """One dimension by path, for callers that need a specific control."""
        for dimension in self.dimensions:
            if dimension.module == module and dimension.key == key:
                return dimension
        raise SpaceError(f"{module}/{key} is not a searchable dimension of this pack")

    def amp_prefix(self, values: Mapping) -> Optional[str]:
        """The module prefix of the selected amp, e.g. `sw50r`.

        Accepts all three spellings that occur in this codebase, which is not
        indulgence — mixing them up silently emptied a spec of its entire EQ fit:

        - the stored integer a decoded vector carries (`2`)
        - the display name a spec may carry (`"SW50R"`)
        - the module prefix `invert(amp=...)` and `fit_graphic_eq(module=...)` use
          throughout (`"sw50r"`)
        """
        selected = _get(values, ("", "selectedAmp"))
        if selected is None:
            return None
        text = str(selected)
        if text in self.amp_by_index:
            return self.amp_by_index[text]
        if text in self.amp_modules:
            return self.amp_modules[text]
        if text in set(self.amp_modules.values()):
            return text
        return None

    # --- conditioning -------------------------------------------------------

    def active(self, values: Mapping) -> List[Dimension]:
        """The dimensions that reach the sound, given these values.

        This is the whole reason the space is not a flat list. A search over the
        inactive amp's tone stack moves nothing and teaches the optimiser that
        tone stacks do nothing.
        """
        prefix = self.amp_prefix(values)
        live = []
        for dimension in self.dimensions:
            if dimension.gate_amp is not None and dimension.gate_amp != prefix:
                continue
            if dimension.gate is not None and not _truthy(_get(values, dimension.gate)):
                continue
            live.append(dimension)
        return live

    def dormant(self, values: Mapping) -> List[Dimension]:
        active = {dimension.path for dimension in self.active(values)}
        return [d for d in self.dimensions if d.path not in active]

    # --- vectors ------------------------------------------------------------

    def encode(self, values: Mapping, missing: str = "refuse"):
        """Human values to a normalised vector in 0..1, in `dimensions` order.

        Fixed length, including the dormant dimensions. An optimiser needs a
        stable vector shape across trials even as switches flip, and dropping a
        dimension mid-run would change what every earlier sample meant.

        A key this space knows and the caller did not supply is **refused** by
        default. It used to encode as 0.0, which is a legitimate coordinate and
        therefore indistinguishable from a deliberate minimum: encoding
        `{"selectedAmp": 2}` alone produced a vector that decoded to a 16 ms delay,
        a mic 40 dB down and a cab panned hard left, and `to_spec` would have
        written all of it. Pass `missing="floor"` to opt into the old behaviour
        when a floor really is what you want.
        """
        require_analysis()
        import numpy as np

        if missing not in ("refuse", "floor"):
            raise SpaceError(f"missing must be 'refuse' or 'floor', not {missing!r}")

        absent = [d.path for d in self.dimensions
                  if _get(values, (d.module, d.key)) is None]
        if absent and missing == "refuse":
            shown = ", ".join(absent[:6])
            more = f" and {len(absent) - 6} more" if len(absent) > 6 else ""
            raise SpaceError(
                f"{len(absent)} of {len(self.dimensions)} dimensions have no value: "
                f"{shown}{more}.\n"
                f"  Encoding them as zero would put a real coordinate — the bottom "
                f"of each range — into the vector, and nothing downstream could tell "
                f"that apart from a deliberate choice. Supply them, or pass "
                f"missing='floor' if the minimum is what you mean."
            )

        out = np.zeros(len(self.dimensions), dtype=np.float64)
        for index, dimension in enumerate(self.dimensions):
            value = _get(values, (dimension.module, dimension.key))
            out[index] = _to_unit(dimension, value)
        return out

    def decode(self, vector) -> Dict[Key, Any]:
        """A normalised vector back to human values, quantised."""
        require_analysis()
        import numpy as np

        array = np.asarray(vector, dtype=np.float64).ravel()
        if len(array) != len(self.dimensions):
            raise SpaceError(
                f"vector has {len(array)} entries; this space has "
                f"{len(self.dimensions)} dimensions"
            )
        return {
            (dimension.module, dimension.key): _from_unit(dimension, float(array[index]))
            for index, dimension in enumerate(self.dimensions)
        }

    # --- output -------------------------------------------------------------

    def to_spec(self, values: Mapping, name: str = "Matched",
                include_dormant: bool = False) -> Dict[str, Any]:
        """The spec `apply_spec.py` consumes.

        Dormant dimensions are left out by default, and that is deliberate: a
        preset that sets the inactive amp's treble to whatever the optimiser last
        sampled is noise in a file someone may read. The switches themselves are
        always written, so what is on and off is explicit.
        """
        prefix = self.amp_prefix(values)
        if prefix is None:
            # Refusing rather than dropping. This silently discarded an entire
            # spectral inversion: `invert()` emits `sw50rEQ/...` keys and no
            # `selectedAmp`, so every amp-owned dimension was skipped and a
            # 14-value inversion came out as 4 parameters with no error and no
            # caveat. A module whose stated principle is "it refuses what it cannot
            # mean" has to refuse this.
            owned = sorted(d.path for d in self.dimensions if d.gate_amp is not None)
            if any(_get(values, (d.rpartition("/")[0], d.rpartition("/")[2])) is not None
                   for d in owned):
                legal = ", ".join(sorted(self.amp_by_index) + sorted(self.amp_modules))
                raise SpaceError(
                    "these values set amp controls but do not say which amp is "
                    "selected, and every amp's controls exist in every preset — so "
                    "there is no way to tell which ones matter.\n"
                    f"  Add a selectedAmp value. Accepted: {legal}, or a module "
                    f"prefix ({', '.join(sorted(set(self.amp_modules.values())))})."
                )

        chosen = self.active(values) if not include_dormant else list(self.dimensions)
        paths = {dimension.path for dimension in chosen}
        parameters = []

        selected = _get(values, ("", "selectedAmp"))
        if selected is not None:
            parameters.append({"module": "", "key": "selectedAmp", "value": selected})

        for dimension in self.dimensions:
            if dimension.key == "selectedAmp":
                continue      # already written above
            if (not include_dormant and dimension.gate_amp is not None
                    and dimension.gate_amp != prefix):
                # Belongs to an amp that is not selected. Not written even though
                # it is a switch: "always write the switches" is about making the
                # effect chain explicit, and another amp's bright switch is not
                # part of this preset's chain.
                continue
            if dimension.path not in paths and not dimension.switch:
                continue
            value = _get(values, (dimension.module, dimension.key))
            if value is None:
                continue
            parameters.append({
                "module": dimension.module,
                "key": dimension.key,
                "value": value,
            })
        return {"name": name, "parameters": parameters}


# --- construction -----------------------------------------------------------


def build(pack_id: str = "morgan", include_needs_review: bool = False,
          amp: Optional[str] = None) -> Space:
    """Read a pack manifest into a searchable space.

    `amp` restricts the space to one amp's modules up front. Leaving it None keeps
    all three and conditions on `selectedAmp` instead, which is what an outer loop
    over discrete topology choices wants.
    """
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    amp_modules = dict(pack.amp_modules)
    prefixes = set(amp_modules.values())
    gates = gate_map(pack)

    # `selectedAmp` stores an integer and `amp_modules` is keyed by display name,
    # so going from a preset value to a module prefix needs both tables.
    selector = pack.parameters.get("/selectedAmp")
    by_index = {}
    if selector is not None and selector.members:
        for stored, name in selector.members.items():
            prefix = amp_modules.get(name)
            if prefix:
                by_index[str(stored)] = prefix

    dimensions: List[Dimension] = []
    excluded: Dict[str, str] = {}

    for path, spec in pack.parameters.items():
        module, _, key = path.rpartition("/")
        reason = _exclusion_reason(spec, include_needs_review)
        if reason:
            excluded[path] = reason
            continue

        owner = _amp_of(module, prefixes)
        if amp is not None and owner is not None and owner != amp:
            excluded[path] = f"belongs to {owner}, not the selected {amp}"
            continue

        try:
            dimension = Dimension(
                module=module,
                key=key,
                kind=spec.kind,
                unit=spec.unit,
                low=spec.min,
                high=spec.max,
                members=dict(spec.members) if spec.members else None,
                quantum=QUANTA.get(spec.unit or spec.kind),
                gate=gates.get(path),
                gate_amp=owner,
            )
            if dimension.continuous:
                # Refuse a metered control with no declared range. Enums and
                # switches carry members instead and have no bounds to check.
                dimension.bounds()
        except SpaceError as e:
            excluded[path] = str(e)
            continue
        dimensions.append(dimension)

    return Space(pack_id=pack_id, dimensions=dimensions,
                 amp_modules=amp_modules, amp_by_index=by_index, excluded=excluded)


def _exclusion_reason(spec, include_needs_review: bool) -> Optional[str]:
    if not spec.writable:
        return "read-only in the manifest"
    if spec.kind in UNSEARCHABLE_KINDS:
        return f"kind {spec.kind!r} is not a searchable quantity"
    if spec.needs_review and not include_needs_review:
        # A guessed kind picks the human-to-stored mapping, so it is the one
        # doubt that writes a plausible number instead of failing.
        return "kind is a bootstrap guess (needs_review)"
    if spec.kind == "enum" and not spec.members:
        # An enum's stored integer means nothing without the table: the plugin
        # never displays it, so the value cannot be chosen on purpose. A *switch*
        # is different and deliberately not excluded here -- its two states are
        # true and false whatever the plugin calls them, `to_binary` maps a bool
        # without consulting members, and members only change how it is displayed.
        # Excluding switches for missing members took every effect on/off control
        # out of the space, so nothing could turn an effect on.
        return "selector members are not known"
    if spec.needs_confirmation:
        return "member names are unconfirmed (needs_confirmation)"
    return None


def _amp_of(module: str, prefixes) -> Optional[str]:
    """Which amp a module belongs to, if any."""
    for prefix in prefixes:
        if module.startswith(prefix):
            return prefix
    return None


def gate_map(pack) -> Dict[str, Key]:
    """Which `*Active` switch each parameter sits behind, derived from the names.

    The manifest does not state this relationship, but it spells it: a switch
    called `<stem>Active` gates the other keys **in its own module** that start
    with the same stem. `compressorActive` gates `compressorCompression`;
    `gateActive` gates `gateThreshold` without gating the rest of `parameters`;
    `leftCabActive` gates `leftCabPan` but not `leftRoomMicLevel`, which has its own
    switch. Longest stem wins, so a key covered by two switches attaches to the more
    specific one.

    **A switch is never gated, by anything.** Not itself, which would make it
    unreachable the moment it went off, and not another switch either. That second
    half is not fastidiousness: Tone King keeps every parameter in one flat module,
    where `/eqActive` (stem `eq`) matches `/eqSectionActive` as though the page
    bypass were a child of the band bypass. That inverted the nesting exactly
    backwards — it reported the section bypass dormant, and reported `eqBand1`
    *active* while the EQ page was bypassed.

    ### What this deliberately does not model

    Section-level bypasses, beyond the one that happens to work. Morgan has five
    `sectionActive` switches and four of them — `ampParameters`, `eqParameters`,
    `pedalParameters`, `fxParameters` — live in modules that contain nothing but
    themselves, while the controls they bypass live in `sw50rAmp`, `sw50rEQ`,
    `drive1`, `delay` and so on. Module-scoped gating therefore gates nothing for
    those four. Only `cabParameters/sectionActive` works, because the cab controls
    happen to share its module.

    That asymmetry is left in place rather than papered over. Guessing which
    modules a section covers would be exactly the kind of unmeasured claim this
    repository refuses: no field states it, and the answer differs per pack. A
    search will therefore move controls inside a bypassed section on four of
    Morgan's five sections — wasted budget, not a wrong value, and
    `unmodelled_sections()` reports it so a caller can say so.

    One narrower limit of name matching, for the same reason: `leftMicType` does not
    start with `leftCab`, so it attaches to `cabParameters/sectionActive` rather
    than to `leftCabActive`. With the section on and the left cab off it is
    reported live. Which switch owns a mic type is genuinely ambiguous from the
    names, so it is not guessed at.
    """
    switches: List[Tuple[str, str, Key]] = []      # (module, stem, key)
    for path, spec in pack.parameters.items():
        module, _, key = path.rpartition("/")
        if spec.kind != "switch" or not key.endswith("Active"):
            continue
        stem = key[: -len("Active")]
        switches.append((module, stem, (module, key)))

    gates: Dict[str, Key] = {}
    for path, spec in pack.parameters.items():
        module, _, key = path.rpartition("/")
        if spec.kind == "switch" and key.endswith("Active"):
            continue      # never gate a gate
        best: Optional[Tuple[int, Key]] = None
        for gate_module, stem, gate in switches:
            if gate_module != module or gate[1] == key:
                continue
            covers = key.startswith(stem) if stem != "section" else True
            if not covers:
                continue
            # `section` is the least specific gate there is, so rank it lowest
            # however long the word happens to be.
            rank = -1 if stem == "section" else len(stem)
            if best is None or rank > best[0]:
                best = (rank, gate)
        if best is not None:
            gates[path] = best[1]
    return gates


def unmodelled_sections(pack) -> List[str]:
    """Section switches that gate nothing, so a report can say which.

    See `gate_map`: a `sectionActive` in a module containing only itself has no
    parameters to gate, and this repository would rather name that than imply the
    conditioning is complete.
    """
    gates = gate_map(pack)
    in_use = set(gates.values())
    idle = []
    for path, spec in pack.parameters.items():
        module, _, key = path.rpartition("/")
        if spec.kind != "switch" or "ection" not in key:
            # Both spellings the two packs use: Morgan's `sectionActive` and Tone
            # King's `eqSectionActive`, `cabSectionActive`, and so on. Checking for
            # the literal "sectionActive" found Morgan's four and none of Tone
            # King's five, which made the report look pack-specific.
            continue
        if (module, key) not in in_use:
            idle.append(path)
    return sorted(idle)


# --- value helpers ----------------------------------------------------------


def _get(values: Mapping, key: Key):
    """Read a value however the caller spelled the key.

    Four spellings occur in this codebase and all four have to work, because
    missing one of them looks like a missing *value*: the tuple form, `module/key`,
    the bare key for a top-level parameter, and `/key` — which is how
    `pack.parameters` itself keys top-level parameters, so it is the spelling a
    caller reading the manifest would naturally use.
    """
    if key in values:
        return values[key]
    for spelling in _spellings(key):
        if spelling in values:
            return values[spelling]
    return None


def _spellings(key: Key) -> Tuple[str, ...]:
    if key[0]:
        return (f"{key[0]}/{key[1]}",)
    return (key[1], f"/{key[1]}")


def require_analysis() -> None:
    """The project's rule: a missing extra prints one actionable line.

    `encode` and `decode` reach for numpy, and used to do it without asking, so a
    bare clone got a raw `ImportError` from six frames down instead of the install
    command. Everything else in this module is deliberately stdlib-only — building
    a space, conditioning it and writing a spec all work with nothing installed.
    """
    from analysis import require

    require("encoding a search vector")


def _truthy(value) -> bool:
    """Is this gate on?

    Delegates to the format layer's reader rather than keeping a fourth opinion.
    A private list here accepted `true/1/on/active` while `format.translate`
    accepted `true/on/yes/1` and *raised* on anything else, so `"yes"` was False
    here and True there — and because this one never raised, a gate holding a label
    it did not recognise silently marked every parameter behind it dormant. Tone
    King declares display labels on all 21 of its switches, so that was live.

    An unrecognised label is treated as off, but only after the shared reader has
    had its say, so the two cannot disagree about `"yes"` or `"Active"` again.
    """
    from format.translate import from_binary

    if isinstance(value, bool) or value is None:
        return bool(value)
    text = str(value).strip()
    if from_binary("switch", text):
        return True
    # The plugin's own labels, which a switch may carry as `members`.
    return text.lower() in ("on", "yes", "active", "enabled")


def _member_index(dimension: Dimension, members: List[str], value) -> int:
    """Which member this value names, by stored integer or by display name.

    Refuses anything else. Falling back to index 0 meant a display name — the very
    spelling `amp_prefix` promises to accept — silently became a *different* amp:
    `encode({"selectedAmp": "SW50R"})` round-tripped to AC20, and so did `99`.
    """
    text = str(value).strip()
    if text in members:
        return members.index(text)
    try:
        return members.index(str(int(float(text))))
    except (ValueError, TypeError):
        pass
    for stored, name in (dimension.members or {}).items():
        if str(name).strip().lower() == text.lower():
            return members.index(str(stored))
    legal = ", ".join(f"{stored}={name}" for stored, name
                      in sorted((dimension.members or {}).items(), key=lambda kv: int(kv[0])))
    raise SpaceError(
        f"{dimension.path}: {value!r} is not one of its members.\n  Accepted: {legal}"
    )


def _to_unit(dimension: Dimension, value) -> float:
    if value is None:
        return 0.0
    if dimension.switch:
        return 1.0 if _truthy(value) else 0.0
    if dimension.kind == "enum":
        members = sorted((dimension.members or {}), key=lambda k: int(k))
        if not members:
            return 0.0
        index = _member_index(dimension, members, value)
        return index / max(1, len(members) - 1)
    low, high = dimension.bounds()
    if high <= low:
        return 0.0
    return (dimension.clamp(value) - low) / (high - low)


def _from_unit(dimension: Dimension, unit: float):
    unit = min(max(unit, 0.0), 1.0)
    if dimension.switch:
        return unit >= 0.5
    if dimension.kind == "enum":
        members = sorted((dimension.members or {}), key=lambda k: int(k))
        if not members:
            return 0
        index = int(round(unit * (len(members) - 1)))
        return int(members[index])
    low, high = dimension.bounds()
    return dimension.quantise(dimension.clamp(low + unit * (high - low)))
