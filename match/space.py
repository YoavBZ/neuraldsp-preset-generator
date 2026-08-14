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
class SelectorCondition:
    """A selector has to hold one of these canonical members for a control to act."""

    selector: Key
    members: Tuple[str, ...]


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
    selector_condition: Optional[SelectorCondition] = None

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
        """The nearest step, kept inside the declared range.

        Clamped *after* stepping, which is the order that matters and was the other
        way round. `tremoloRate` is declared 0.15–15 Hz with a 1 Hz step, so
        `_from_unit(dim, 0.0)` clamped 0.15 into range and the step then rounded it to
        **0.0** — below the plugin's own minimum, in a value the search would go on to
        write. `apply_spec` refuses it, so the failure surfaced as a search that
        produced an unusable preset rather than as a wrong number.

        A clamped result may therefore not be on the step grid, and that is correct:
        the endpoint of a declared range is legal by definition, whether or not it
        happens to be a whole number of steps from zero.
        """
        if not self.quantum:
            return value
        stepped = round(float(value) / self.quantum) * self.quantum
        low, high = self.bounds()
        # Rounding to a step can leave a long float tail; the spec is read by
        # people as well as by apply_spec.py.
        return round(min(max(stepped, low), high), 6)


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
    # Each gate switch's own gate, so `active()` can walk the chain. Kept
    # separately from `dimensions` because a gate may be a parameter the space
    # excludes — Tone King's page bypasses are `internal` — and it still gates.
    gate_parents: Dict[Key, Key] = field(default_factory=dict)

    # --- lookups ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.dimensions)

    def by_path(self, module: str, key: str) -> Dimension:
        """One dimension, for callers that need a specific control."""
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

        A gate the caller did not mention leaves its subtree live. Reading an
        absent switch as *off* discarded values silently: `to_spec({"selectedAmp":
        2, "sw50rEQ/sw50rEQBand1": 6.0})` emitted only `selectedAmp`, because no
        `sw50rEQActive` was supplied. Absence is not a measurement of off — the
        template's own switch decides, and the caller supplied a value for the
        control either way.

        Gates compose. `cabParameters/sectionActive` gates `leftCabActive`, which
        gates `leftCabPan`, and checking only the immediate gate reported the pan
        live with the whole cab section bypassed — 15 of Morgan's 21 cab dimensions
        were reported live behind a switch that silences all 21. Every gate up the
        chain has to be on.
        """
        prefix = self.amp_prefix(values)
        live = []
        for dimension in self.dimensions:
            if dimension.gate_amp is not None and dimension.gate_amp != prefix:
                continue
            condition = dimension.selector_condition
            if condition is not None:
                selected = _get(values, condition.selector)
                if selected is not None and _selector_token(selected) not in condition.members:
                    continue
            if self._gated_off(dimension, values) is None:
                live.append(dimension)
        return live

    def _gated_off(self, dimension: Dimension, values: Mapping) -> Optional[str]:
        """The path of the first switch up this dimension's chain that is off."""
        gate = dimension.gate
        seen = set()
        while gate is not None and gate not in seen:
            seen.add(gate)
            value = _get(values, gate)
            if value is not None and not _truthy(value):
                return f"{gate[0]}/{gate[1]}" if gate[0] else gate[1]
            gate = self.gate_parents.get(gate)
        return None

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
        from analysis import require

        require("encoding a search vector")
        import numpy as np

        if missing not in ("refuse", "floor"):
            raise SpaceError(f"missing must be 'refuse' or 'floor', not {missing!r}")

        absent = [d.path for d in self.dimensions
                  if _get(values, (d.module, d.key)) is None]
        if absent and missing == "refuse":
            shown = ", ".join(absent[:4])
            more = f", and {len(absent) - 4} more" if len(absent) > 4 else ""
            raise SpaceError(
                f"{len(absent)} of {len(self.dimensions)} dimensions have no value, "
                f"so there is nothing to encode them as.\n"
                f"  Start from a complete set — `decode()` of another vector, or a "
                f"template read through `format.structured` — and override the few "
                f"you mean to change. Pass missing='floor' only if the bottom of "
                f"every missing range really is what you want: that is a legitimate "
                f"coordinate, so nothing downstream can tell it from a deliberate "
                f"choice.\n"
                f"  Missing: {shown}{more}."
            )

        out = np.zeros(len(self.dimensions), dtype=np.float64)
        for index, dimension in enumerate(self.dimensions):
            value = _get(values, (dimension.module, dimension.key))
            out[index] = _to_unit(dimension, value)
        return out

    def decode(self, vector) -> Dict[Key, Any]:
        """A normalised vector back to human values, quantised."""
        from analysis import require

        require("decoding a search vector")
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
                raise SpaceError(self._no_amp_message(_get(values, ("", "selectedAmp"))))

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

    def _no_amp_message(self, supplied) -> str:
        """Why the spec was refused, saying which value was the problem.

        Two refusals landed in the same commit and disagreed: `invert`'s named the
        offending amp and this one did not, so an *unrecognised* `selectedAmp` was
        reported as an *absent* one — "do not say which amp is selected" for a
        value of `"Marshall"`, which never appeared in the message.
        """
        stored = ", ".join(f"{index}={self.amp_by_index[index]}"
                           for index in sorted(self.amp_by_index, key=str))
        names = ", ".join(sorted(self.amp_modules))
        if supplied is None:
            opening = ("these values set amp controls but do not say which amp is "
                       "selected")
        else:
            opening = (f"these values set amp controls, but {supplied!r} is not an "
                       f"amp this pack has")
        return (
            f"{opening}, and every amp's controls exist in every preset — so there "
            f"is no way to tell which ones matter.\n"
            f"  Set selectedAmp to a display name ({names}), or to the stored index "
            f"or module prefix ({stored})."
        )


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
    conditions = selector_conditions(pack)

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
                selector_condition=conditions.get(path),
            )
            if dimension.continuous:
                # Refuse a metered control with no declared range. Enums and
                # switches carry members instead and have no bounds to check.
                dimension.bounds()
        except SpaceError as e:
            excluded[path] = str(e)
            continue
        dimensions.append(dimension)

    # A gate's own gate, for every gate in use, whether or not it survived
    # exclusion above.
    in_use = set(gates.values())
    parents = {gate: gates[f"{gate[0]}/{gate[1]}" if gate[0] else f"/{gate[1]}"]
               for gate in in_use
               if (f"{gate[0]}/{gate[1]}" if gate[0] else f"/{gate[1]}") in gates}

    return Space(pack_id=pack_id, dimensions=dimensions,
                 amp_modules=amp_modules, amp_by_index=by_index, excluded=excluded,
                 gate_parents=parents)


def _exclusion_reason(spec, include_needs_review: bool) -> Optional[str]:
    if not spec.writable:
        return "read-only in the manifest"
    if not spec.searchable:
        return "writable utility control, excluded from tone matching"
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

    **No switch is gated by a switch whose stem is a prefix of its own name.** Not
    by itself, which would make it unreachable the moment it went off, and not by a
    prefix sibling. That second half is not fastidiousness: Tone King keeps every
    parameter in one flat module, where `/eqActive` (stem `eq`) matches
    `/eqSectionActive` as though the page bypass were a child of the band bypass.
    That inverted the nesting exactly backwards — it reported the section bypass
    dormant, and reported `eqBand1` *active* while the EQ page was bypassed.

    A `sectionActive` gate is exempt, because it is a genuine parent rather than a
    prefix accident: `cabParameters/sectionActive` really does bypass
    `cabParameters/leftCabActive`. Ruling out *every* switch-on-switch gate instead
    was the first fix tried, and it cost four correct gates on Morgan
    (`leftCabActive`, `rightCabActive`, `leftRoomActive`, `rightRoomActive`) while
    changing nothing on Tone King, whose defect was the prefix match alone.

    ### What this deliberately does not model

    Section-level bypasses, beyond the one that happens to work. Morgan has five
    `sectionActive` switches and four of them — `ampParameters`, `eqParameters`,
    `pedalParameters`, `fxParameters` — live in modules that contain nothing but
    themselves, while the controls they bypass live in `sw50rAmp`, `sw50rEQ`,
    `drive1`, `delay` and so on. Module-scoped gating therefore gates nothing for
    those four. Only `cabParameters/sectionActive` works, because the cab controls
    happen to share its module — 6 of the 21 cab dimensions directly, the other 14
    through the four cab and room switches it gates, which `Space.active()` reaches
    by walking the chain.

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
        is_bypass = spec.kind == "switch" and key.endswith("Active")
        best: Optional[Tuple[int, Key]] = None
        for gate_module, stem, gate in switches:
            if gate_module != module or gate[1] == key:
                continue
            section = stem == "section"
            if is_bypass and not section:
                continue      # a prefix sibling is not this switch's parent
            covers = True if section else key.startswith(stem)
            if not covers:
                continue
            # `section` is the least specific gate there is, so rank it lowest
            # however long the word happens to be.
            rank = -1 if section else len(stem)
            if best is None or rank > best[0]:
                best = (rank, gate)
        if best is not None:
            gates[path] = best[1]
    return gates


def selector_conditions(pack) -> Dict[str, SelectorCondition]:
    """Explicit selector ownership for controls a flat namespace cannot imply.

    Module prefixes express Morgan's amp ownership. Tone King's Rhythm and Lead
    controls all live at the top level, so their spelling alone cannot tell the
    search which channel is audible. The manifest states those few relationships
    explicitly; this resolves labels to stored members once and refuses stale
    paths or impossible member names while building the space.
    """
    from packs.loader import PackError

    found: Dict[str, SelectorCondition] = {}
    for path, row in pack.search_conditions.items():
        if path not in pack.parameters:
            raise SpaceError(
                f"search condition names unknown parameter {path!r} in "
                f"packs/{pack.pack_id}/manifest.json"
            )
        if not isinstance(row, dict):
            raise SpaceError(f"search condition for {path} must be an object")
        raw_selector = row.get("selector")
        if not isinstance(raw_selector, str):
            raise SpaceError(f"search condition for {path} needs a selector path")
        selector_path = raw_selector if "/" in raw_selector else f"/{raw_selector}"
        selector = pack.parameters.get(selector_path)
        if selector is None or selector.kind != "enum" or not selector.members:
            raise SpaceError(
                f"search condition for {path} names {raw_selector!r}, which is not "
                "a declared selector with members"
            )
        raw_members = row.get("members")
        if not isinstance(raw_members, list) or not raw_members:
            raise SpaceError(f"search condition for {path} needs a non-empty members list")
        accepted = []
        for member in raw_members:
            try:
                stored = pack.to_stored(selector, member, warnings=[])
            except PackError as error:
                raise SpaceError(f"search condition for {path}: {error}") from error
            accepted.append(_selector_token(stored))
            accepted.append(_selector_token(member))
        module, _, key = selector_path.rpartition("/")
        found[path] = SelectorCondition((module, key), tuple(sorted(set(accepted))))
    return found


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
            # King's `eqSectionActive`, `cabSectionActive` and so on. Checking for
            # the literal "sectionActive" found Morgan's four and none of Tone
            # King's four, which made the report look pack-specific. Tone King
            # spells three more — `modSectionActive`, `pitchSectionActive`,
            # `wahSectionActive` — but declares them `internal`, so the `kind`
            # test above leaves them out along with the rest of its read-only state.
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
    """The other ways this key may be spelled, `module/key` and `/key`."""
    if key[0]:
        return (f"{key[0]}/{key[1]}",)
    return (key[1], f"/{key[1]}")


# What a switch value may say to mean "on". `format.translate.from_binary` reads
# only `"true"` and `"1"` — the two spellings that occur in a preset file — so it
# cannot be the whole answer here: a gate arrives as whatever the caller or the
# optimiser is holding, which is a `bool`, a float out of `decode`, or one of the
# display labels a manifest declares. Tone King labels all 21 of its switches.
SWITCH_ON_LABELS = frozenset({"true", "1", "on", "yes", "active", "enabled"})


def _truthy(value) -> bool:
    """Is this gate on?

    Two ways this got it wrong, both measured:

    **A private vocabulary that disagreed with the writer.** It accepted
    `true/1/on/active` while claiming to share `format.translate`'s list, and an
    unrecognised label silently marked every parameter behind the gate dormant.
    The vocabulary is now named above, one place, and stated to be wider than the
    file format's on purpose rather than by accident.

    **A number other than 1 read as off.** Delegating the string test to
    `from_binary` also delegated the *numeric* test, and that reader matches the
    literal `"1"` only: `_truthy(1.0)` and `_truthy(2)` both came back False while
    `to_binary("switch", 1.0)` writes `"true"`. So `space.active()` reported a
    delay's time and mix dormant, `to_spec` dropped both, and the preset came out
    with the delay switched *on* and the template's own time and mix. Anything
    numeric and non-zero is on, which is what every other layer in this repository
    already means by a numeric switch, and it covers a numpy scalar out of `decode`
    as well as a plain float.
    """
    if isinstance(value, bool) or value is None:
        return bool(value)
    text = str(value).strip().lower()
    if text in SWITCH_ON_LABELS:
        return True
    try:
        return float(text) != 0.0
    except (TypeError, ValueError):
        return False


def _selector_token(value) -> str:
    """Canonical stored-member spelling for an enum value already in a vector."""
    text = str(value).strip()
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text.casefold()
    return str(int(number)) if number.is_integer() else format(number, ".12g")


def _member_index(dimension: Dimension, members: List[str], value) -> int:
    """Which member this value names, by stored integer or by display name.

    Refuses anything else. Falling back to index 0 meant a display name — the very
    spelling `amp_prefix` promises to accept — silently became a *different* amp:
    `encode({"selectedAmp": "SW50R"})` round-tripped to AC20, and so did `99`.

    A non-integral number is refused rather than truncated, because the two ends of
    the round-trip truncate opposite ways: this function floored `1.7` to member 1
    (PR12) while `pack.to_stored` rounds it to `"2"` (SW50R). An optimiser that has
    not quantised its enum coordinate should hear about it, not get a different amp
    at each end.
    """
    text = str(value).strip()
    if text in members:
        return members.index(text)
    try:
        number = float(text)
    except (TypeError, ValueError, OverflowError):
        number = None
    if number is not None and float(number).is_integer():
        try:
            return members.index(str(int(number)))
        except ValueError:
            pass
    for stored, name in (dimension.members or {}).items():
        if str(name).strip().lower() == text.lower():
            return members.index(str(stored))
    legal = ", ".join(f"{stored}={name}" for stored, name
                      in sorted((dimension.members or {}).items(), key=lambda kv: int(kv[0])))
    detail = (" A selector's value has to name one member exactly; there is no "
              "member between two members." if number is not None else "")
    raise SpaceError(
        f"{dimension.path}: {value!r} is not one of its members.\n"
        f"  Accepted: {legal}.{detail}"
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
