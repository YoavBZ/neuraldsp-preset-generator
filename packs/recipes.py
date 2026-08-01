"""Composable tone recipes: load them, resolve them, stack them.

A recipe is a partial spec for one layer of a preset — amp, compressor, drive,
EQ, cab, delay, reverb, output staging. A preset is built by stacking one per
layer and then adapting the values to the actual song.

Two things in a recipe need resolving before it can be applied:

- **`{amp}` templates.** The graphic EQ is per-amp (`pr12EQ`, `sw50rEQ`,
  `ac20EQ`), so EQ recipes are written against `{amp}EQ` and substituted with
  whichever amp is live. An EQ recipe applied to the wrong amp does nothing
  audible, which is a silent failure worth removing from human hands.
- **Note divisions.** `{"note": "1/4"}` becomes milliseconds (or Hz) once a
  tempo is known, so a recipe stays correct at any tempo without needing the
  plugin's sync selector.

Both live here so they are implemented once and used by both the writer and the
tests, rather than restated in four documents.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from packs.loader import Pack, PackError, PACKS_DIR
from packs.timing import TimingError, note_hz, note_ms

AMP_TEMPLATE = "{amp}"


@dataclass(frozen=True)
class Recipe:
    """One layer's worth of settings, with why you'd reach for it."""

    layer: str
    id: str
    title: str
    use_when: str
    parameters: List[Dict[str, Any]]
    note: Optional[str] = None

    @property
    def ref(self) -> str:
        return f"{self.layer}/{self.id}"


def load_recipes(pack_id: str = "morgan") -> Dict[str, Dict[str, Recipe]]:
    """All recipes for a pack, as layer -> id -> Recipe."""
    path = PACKS_DIR / pack_id / "recipes.json"
    if not path.exists():
        raise PackError(f"No recipes for pack {pack_id!r} (looked for {path}).")
    raw = json.loads(path.read_text())
    return {
        layer: {
            rid: Recipe(
                layer=layer,
                id=rid,
                title=entry["title"],
                use_when=entry["use_when"],
                parameters=entry["parameters"],
                note=entry.get("note"),
            )
            for rid, entry in group.items()
        }
        for layer, group in raw["layers"].items()
    }


def get_recipe(ref: str, pack_id: str = "morgan") -> Recipe:
    """Look up one recipe by its `layer/id` reference."""
    layer, _, rid = ref.partition("/")
    if not layer or not rid:
        raise PackError(
            f"{ref!r} is not a recipe reference. Use layer/id, e.g. "
            f"amp/pr12-clean or delay/classic-lead."
        )
    recipes = load_recipes(pack_id)
    if layer not in recipes:
        raise PackError(
            f"No recipe layer {layer!r}.\n  Layers: {', '.join(sorted(recipes))}"
        )
    if rid not in recipes[layer]:
        raise PackError(
            f"No recipe {ref!r}.\n"
            f"  In {layer}: {', '.join(sorted(recipes[layer]))}"
        )
    return recipes[layer][rid]


def expand_amp(entry: Dict[str, Any], amp_prefix: Optional[str]) -> Dict[str, Any]:
    """Substitute `{amp}` in an entry's module and key.

    Raises if a template is present but no amp is known — silently leaving
    `{amp}EQ` in place would produce a parameter that matches nothing.
    """
    module, key = entry["module"], entry["key"]
    if AMP_TEMPLATE not in module and AMP_TEMPLATE not in key:
        return entry
    if not amp_prefix:
        raise PackError(
            f"{module}/{key} is templated on the live amp, but no amp is set.\n"
            f"  Include a selectedAmp parameter (or an amp/… recipe) so the EQ "
            f"targets the right module."
        )
    return {
        **entry,
        "module": module.replace(AMP_TEMPLATE, amp_prefix),
        "key": key.replace(AMP_TEMPLATE, amp_prefix),
    }


def amp_prefix_for(pack: Pack, selected: Any) -> Optional[str]:
    """Module prefix ('sw50r') for a selectedAmp value, given by name or index."""
    prefixes = pack.amp_modules
    if not prefixes:
        return None
    text = str(selected).strip()
    for name, prefix in prefixes.items():
        if text.lower() == name.lower():
            return prefix
    spec = pack.get("", "selectedAmp")
    if spec is not None:
        name = spec.member_name(text)
        if name:
            return prefixes.get(name)
    return None


def resolve_value(value: Any, spec, bpm: Optional[float]) -> Any:
    """Turn a `{"note": …}` value into a number; pass anything else through.

    `bpm` may be carried on the value itself, which is how a hand-written spec
    supplies it; `bpm` here is the fallback for a recipe that doesn't.
    """
    if not isinstance(value, dict):
        return value
    if "note" not in value:
        raise PackError(
            f'{spec.path}: object values must contain a "note", e.g. '
            f'{{"note": "1/8 dotted", "bpm": 120}}'
        )
    unknown = set(value) - {"note", "bpm"}
    if unknown:
        raise PackError(f"{spec.path}: unexpected field(s) {sorted(unknown)} in a note value.")

    tempo = value.get("bpm", bpm)
    if tempo is None:
        raise PackError(
            f"{spec.path}: a note division needs a tempo. Pass --bpm, or write "
            f'{{"note": {value["note"]!r}, "bpm": 120}}. Read the song\'s tempo '
            f"from the user, or from the preset's delayTempo."
        )

    if spec.unit == "ms":
        convert = note_ms
    elif spec.unit == "hz":
        convert = note_hz
    else:
        raise PackError(
            f"{spec.path}: a note division only makes sense for a time (ms) or "
            f"rate (hz) parameter; this is {spec.unit or spec.kind}."
        )

    try:
        return round(convert(tempo, value["note"]), 4)
    except TimingError as e:
        raise PackError(f"{spec.path}: {e}") from e


def selected_amp_in(refs: Iterable[str], pack_id: str = "morgan") -> Optional[Any]:
    """The amp a recipe stack selects, if any. Last one wins, matching apply order."""
    chosen = None
    for ref in refs:
        for entry in get_recipe(ref, pack_id).parameters:
            if entry["key"] == "selectedAmp":
                chosen = entry["value"]
    return chosen


def stack(
    refs: Iterable[str],
    pack: Pack,
    amp_prefix: Optional[str] = None,
    pack_id: str = "morgan",
) -> List[Dict[str, Any]]:
    """Concatenate several recipes into one list of spec entries.

    Later recipes win on conflict, so ordering is the caller's lever. `{amp}` is
    resolved against `amp_prefix` when given, else against whichever amp the
    stack itself selects — so an `amp/…` recipe listed before an `eq/…` one just
    works.
    """
    chosen = list(refs)
    if amp_prefix is None:
        selected = selected_amp_in(chosen, pack_id)
        if selected is not None:
            amp_prefix = amp_prefix_for(pack, selected)

    return [
        expand_amp(entry, amp_prefix)
        for ref in chosen
        for entry in get_recipe(ref, pack_id).parameters
    ]
