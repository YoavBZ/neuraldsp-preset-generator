#!/usr/bin/env python3
"""Declare set 4 (fresh held-out confirmation material): kept parts and exclusions.

    .venv/bin/python research/validation_set4.py \\
      --catalog ~/ndsp-presets/references/datasets-set4/catalog.json \\
      --crops ~/ndsp-presets/references/validation-crops-set4 \\
      --json docs/validation-set4.json

Reads only the catalogue and the crop records (JSON). It opens no audio, starts no
plugin and scores nothing. `docs/validation-set4-plan.md` states the rules: set 3's
(`research/validation_set3.py`, whose exclusion and mark functions are reused), with
every band held out, so there is no draw and no folds.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import validation_set3 as vs3  # noqa: E402

DECLARED = "2026-10-10"
SPLIT = "held_out"


def _pairing_failure(p) -> str:
    wf = p["waveform"]
    if not wf.get("windows"):
        return ("fails both same-take tests: no 20-s window where both tracks play "
                f"(the DI is {p['di_seconds']} s long)")
    return ("fails both same-take tests: waveform test "
            f"{wf['in_step_fraction']:.0%} of {wf['windows']} windows in step, "
            f"median peak-to-sidelobe {wf['median_peak_to_sidelobe']}")


def build(catalog_path: pathlib.Path, crops: pathlib.Path):
    cat = json.loads(catalog_path.read_text())
    recs = vs3.crop_records(crops)
    kept, excluded = [], []
    for s in cat["sessions"]:
        if s.get("band_in_earlier_set"):
            raise ValueError(f"{s['group']} is in an earlier set: it cannot be fresh held-out material")
        for p in s["parts"]:
            if not p.get("usable_rule"):
                excluded.append({"session_key": s["key"], "band": s["group"], "song": s["song"],
                                 "part": p["part"], "source": s["source"], "slug": None,
                                 "crop_record_sha256": None,
                                 "reasons": [p.get("excluded") or _pairing_failure(p)]})
                continue
            crop = recs.get((s["key"], p["part"]))
            why = vs3.exclusion_reasons(p, crop[1] if crop else None)
            base = {"session_key": s["key"], "band": s["group"], "song": s["song"],
                    "part": p["part"], "source": s["source"]}
            if why:
                excluded.append({**base, "slug": crop[0] if crop else None,
                                 "crop_record_sha256": crop[2] if crop else None, "reasons": why})
                continue
            slug, rec, rec_sha = crop
            wf, lag = p["waveform"], rec["lag"]
            onset_clear = lag["onset_runner_up"] is not None and lag["onset_runner_up"] < vs3.ONSET_CLEAR
            onset = ("unclear" if not onset_clear else
                     "agrees" if abs(lag["onset_lag_samples"] - lag["lag_samples"]) <= vs3.ONSET_AGREE_SAMPLES
                     else "disagrees")
            kept.append({
                "slug": slug, "band": s["group"], "song": s["song"], "part": p["part"],
                "tone": vs3._tone(p["part"]), "split": SPLIT, "fold": None,
                "session_key": s["key"], "source": s["source"],
                "gain_class": p["gain_class"], "gain_class_crop": rec["gain_class_crop"],
                "gain_confidence": p["gain_confidence"],
                "gain_confidence_reasons": p["gain_confidence_reasons"],
                "clean_vs_driven": p["clean_vs_driven"],
                "level_slope": p["gain_measures"]["level_slope"],
                "nonlinear_to_linear_db": p["gain_measures"]["nonlinear_to_linear_db"],
                "lag_samples": lag["lag_samples"],
                "judge_lag_samples": lag["lag_samples"] - vs3.JUDGE_LATENCY,
                "lag_samples_native": lag["lag_samples_native"], "native_rate": lag["native_rate"],
                "polarity": lag["polarity"],
                "pairing_test": "envelope+waveform" if p["repo_usable"] else "waveform",
                "reference": p["reference"], "di": p["di"],
                "waveform": {"windows": wf["windows"],
                             "passing_windows": round(wf["windows"] * wf["in_step_fraction"]),
                             "median_peak_to_sidelobe": wf["median_peak_to_sidelobe"],
                             "precise_fraction": wf["precise_fraction"]},
                "onset_check": {"result": onset, "onset_lag_samples": lag["onset_lag_samples"],
                                "runner_up": None if lag["onset_runner_up"] is None
                                else round(lag["onset_runner_up"], 3)},
                "marks": vs3.marks(p), "catalog_flags": p["flags"],
                "licence": s["source"],
                "crop": {"excerpt_start_s": rec["excerpt_start_s"],
                         "di_sha256": rec["outputs"]["di"]["sha256"],
                         "reference_sha256": rec["outputs"]["reference"]["sha256"],
                         "record_sha256": rec_sha},
            })

    sessions = [{"key": s["key"], "band": s["group"], "song": s["song"], "source": s["source"],
                 "path": s["path"], "url": s.get("url"), "archive_sha256": s["archive_sha256"],
                 "licence_extra": s.get("licence_extra"),
                 "split": SPLIT, "fold": None,
                 "kept_parts": sum(1 for p in kept if p["session_key"] == s["key"]),
                 "dis": [{"part": p["part"], "di": f"{s['path']}/{p['di']}",
                          "di_clip_runs": p["di_clip"]["runs_ge3"],
                          "clipped": p["di_clip"]["runs_ge3"] >= vs3.CLIP_RUNS}
                         for p in s["parts"] if p.get("di")]}
                for s in cat["sessions"]]

    def count(rows, key):
        return dict(sorted(collections.Counter(key(r) for r in rows).items(), key=str))

    tones = {(p["session_key"], p["tone"]): p for p in kept}.values()
    kept.sort(key=lambda p: (p["band"], p["slug"]))
    return {
        "schema": "validation-set4-1",
        "declared": DECLARED,
        "plan": "docs/validation-set4-plan.md",
        "catalog": {"path": "~/ndsp-presets/references/datasets-set4/catalog.json",
                    "sha256": vs3._sha(catalog_path), "schema": cat["schema"]},
        "root": "~/ndsp-presets/references/datasets-set4",
        "crops_root": "~/ndsp-presets/references/validation-crops-set4",
        "rules": {
            "same_take": "waveform test (catalog rules.supplementary_pairing), as set 3",
            "min_passing_waveform_windows": vs3.MIN_WAVEFORM_WINDOWS,
            "clipped_di_runs": vs3.CLIP_RUNS,
            "two_lag_clusters": "catalogue flag 'lag ambiguous'",
            "split": "every band held out: no draw, no folds",
            "judge_lag": f"lag_samples - {vs3.JUDGE_LATENCY} (48 kHz)",
            "lag_sign": cat["rules"]["lag_sign"],
            "band_weighting": "recommended as set 3's amendment (4): each band's parts weigh 1/n; "
                              "a confirmation plan adopts or overrides it explicitly",
        },
        "held_out_bands": sorted({s["band"] for s in sessions}),
        "licences": cat["licences"],
        "unpaired": cat["unpaired"],
        "counts": {
            "declared_parts": len(kept) + len(excluded), "excluded": len(excluded), "kept": len(kept),
            "kept_tones": len(tones),
            "by_band": count(kept, lambda p: p["band"]),
            "by_band_tones": count(tones, lambda p: p["band"]),
            "by_gain_class": count(kept, lambda p: p["gain_class"]),
            "by_band_gain_class": count(kept, lambda p: f"{p['band']}/{p['gain_class']}"),
            "by_gain_class_crop": count(kept, lambda p: p["gain_class_crop"]),
            "onset_check": count(kept, lambda p: p["onset_check"]["result"]),
        },
        "sessions": sessions,
        "parts": kept,
        "excluded": sorted(excluded, key=lambda p: (p["band"], p["song"], p["part"])),
        "held_out_uses": [],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    home = pathlib.Path.home() / "ndsp-presets" / "references"
    ap.add_argument("--catalog", type=pathlib.Path, default=home / "datasets-set4" / "catalog.json")
    ap.add_argument("--crops", type=pathlib.Path, default=home / "validation-crops-set4")
    ap.add_argument("--json", type=pathlib.Path, required=True)
    args = ap.parse_args()
    out = build(args.catalog.expanduser(), args.crops.expanduser())
    args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
