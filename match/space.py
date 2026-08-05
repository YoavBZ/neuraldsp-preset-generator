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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

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
    ui: Optional[str] = None

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

    def by_path(self) -> Dict[str, Dimension]:
        return {dimension.path: dimension for dimension in self.dimensions}

    def __len__(self) -> int:
        return len(self.dimensions)

    def amp_prefix(self, values: Mapping) -> Optional[str]:
        """The module prefix of the selected amp, e.g. `sw50r`.

        Accepts either the stored integer or the display name, because a spec may
        legitimately carry `"SW50R"` and a decoded vector carries `2`.
        """
        selected = _get(values, ("", "selectedAmp"))
        if selected is None:
            return None
        text = str(selected)
        if text in self.amp_by_index:
            return self.amp_by_index[text]
        return self.amp_modules.get(text)

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

    def encode(self, values: Mapping):
        """Human values to a normalised vector in 0..1, in `dimensions` order.

        Fixed length, including the dormant dimensions. An optimiser needs a
        stable vector shape across trials even as switches flip, and dropping a
        dimension mid-run would change what every earlier sample meant.
        """
        import numpy as np

        out = np.zeros(len(self.dimensions), dtype=np.float64)
        for index, dimension in enumerate(self.dimensions):
            value = _get(values, (dimension.module, dimension.key))
            out[index] = _to_unit(dimension, value)
        return out

    def decode(self, vector) -> Dict[Key, Any]:
        """A normalised vector back to human values, quantised."""
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
        chosen = self.active(values) if not include_dormant else list(self.dimensions)
        paths = {dimension.path for dimension in chosen}
        prefix = self.amp_prefix(values)
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
                ui=spec.ui,
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
    called `<stem>Active` gates the other keys in its module that start with the
    same stem. `compressorActive` gates `compressorCompression`; `gateActive` gates
    `gateThreshold` without gating the rest of `parameters`; `leftCabActive` gates
    `leftCabPan` but not `leftRoomMicLevel`, which has its own switch.

    `sectionActive` is the exception and is handled as one: its stem names nothing,
    and it gates its whole module.

    Longest stem wins, so a key covered by two switches is attached to the more
    specific one. Nothing gates a switch on itself — that would make it
    unreachable the moment it went off.
    """
    switches: List[Tuple[str, str, Key]] = []      # (module, stem, key)
    for path, spec in pack.parameters.items():
        module, _, key = path.rpartition("/")
        if spec.kind != "switch" or not key.endswith("Active"):
            continue
        stem = key[: -len("Active")]
        switches.append((module, stem, (module, key)))

    gates: Dict[str, Key] = {}
    for path in pack.parameters:
        module, _, key = path.rpartition("/")
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


# --- value helpers ----------------------------------------------------------


def _get(values: Mapping, key: Key):
    """Read a value spelled either as a tuple or as "module/key"."""
    if key in values:
        return values[key]
    path = f"{key[0]}/{key[1]}" if key[0] else key[1]
    return values.get(path)


def _truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "on", "active")
    return bool(value)


def _to_unit(dimension: Dimension, value) -> float:
    if value is None:
        return 0.0
    if dimension.switch:
        return 1.0 if _truthy(value) else 0.0
    if dimension.kind == "enum":
        members = sorted((dimension.members or {}), key=lambda k: int(k))
        if not members:
            return 0.0
        try:  # noqa: SIM105 - the fallback is meaningful, not a swallow
            index = members.index(str(int(value)))
        except (ValueError, TypeError):
            index = 0
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
