"""Structural and renderer identity checks for recorded DI/reference pairs."""

import json
import pathlib
import re

RENDER_IDENTITY = (
    "renderer_id", "plugin_version", "renderer_build", "sample_rate",
    "block_size", "quality_mode",
)


def read_pairing(path):
    try:
        document = json.loads(pathlib.Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read paired provenance {path}: {error}") from error
    return validate_pairing(document)


def validate_pairing(document, *, compact=False):
    if not isinstance(document, dict) or document.get("schema") != "paired-di-reference-1":
        raise ValueError("paired provenance must be a paired-di-reference-1 object")

    def text_field(obj, field, label):
        if not isinstance(obj.get(field), str) or not obj[field].strip():
            raise ValueError(f"paired provenance {label}.{field} must be a nonempty string")

    def digest(obj, field, label):
        value = obj.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"paired provenance {label}.{field} must be a SHA-256 digest")

    for section in ("preset", "probe_di", "reference", "renderer"):
        obj = document.get(section)
        if not isinstance(obj, dict):
            raise ValueError(f"paired provenance {section} must be an object")
        if section != "renderer":
            text_field(obj, "path", section)
            digest(obj, "sha256", section)
        if section in ("probe_di", "reference"):
            digest(obj, "audio_sha256", section)
    renderer = document["renderer"]
    for field in ("renderer_id", "renderer_build", "quality_mode"):
        text_field(renderer, field, "renderer")
    if "plugin_version" not in renderer or not isinstance(renderer["plugin_version"], (str, type(None))):
        raise ValueError("paired provenance renderer.plugin_version must be a string or null")
    for field in ("sample_rate", "block_size"):
        if type(renderer.get(field)) is not int or renderer[field] <= 0:
            raise ValueError(f"paired provenance renderer.{field} must be a positive integer")
    if compact:
        text_field(document, "path", "sidecar")
        digest(document, "sha256", "sidecar")
    else:
        text_field(document, "pack", "root")
    return document


def same_renderer(recorded, current):
    return all(field in recorded and recorded[field] == current.get(field)
               for field in RENDER_IDENTITY)
