"""One loader for every capture file (`docs/pipeline-fix-plan.md`, L1a): A2 containers (their largest submodel) and A1
WaveNet files (old layer keys translated). Files are read as data; `nam` is imported only to load one, so this module
runs in `tools/nam-venv` (`python -I`), and its pure part in the main environment's tests.
"""
from __future__ import annotations

import copy
import json
import pathlib


def modern(d):
    """An A1 WaveNet file's layers in the keys release 0.13 reads; anything newer unchanged. Gated layers are refused."""
    d = copy.deepcopy(d)
    for lc in d["config"]["layers"]:
        if "head_size" not in lc:
            continue
        if lc.pop("gated", False):
            raise ValueError("gated A1 layers are not translated")
        lc["head"] = {"out_channels": lc.pop("head_size"), "kernel_size": 1, "bias": lc.pop("head_bias")}
        if isinstance(lc["activation"], str):
            lc["activation"] = [lc["activation"]] * len(lc["dilations"])
    return d


def inner(d):
    """The model dict to load: a container's largest submodel, an A1 WaveNet translated, anything else as it is."""
    if d["architecture"] == "SlimmableContainer":
        d = max(d["config"]["submodels"], key=lambda s: s["max_value"])["model"]
    return modern(d) if d["architecture"] == "WaveNet" else d


def load(path):
    """-> (model in eval mode, the file's metadata)."""
    from nam.models._from_nam import init_from_nam

    d = json.loads(pathlib.Path(path).read_text())
    return init_from_nam(inner(d)).eval(), d.get("metadata", {})
