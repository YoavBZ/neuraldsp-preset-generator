#!/usr/bin/env python3
"""Declare set 3 (heavier-tone validation recordings): exclusions, split and folds.

    python research/validation_set3.py \\
      --catalog ~/ndsp-presets/references/datasets-set3/catalog.json \\
      --crops ~/ndsp-presets/references/validation-crops-set3 \\
      --json docs/validation-set3.json

Reads only the catalogue and the crop records (JSON). It opens no audio, starts no
plugin and scores nothing. `docs/validation-set3.md` states the rules; this is them, so
the committed declaration can be rebuilt from the same two inputs.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import random

DECLARED = "2026-10-07"
SEED = 20261007                  # one generator: held-out draw, then the folds
STRATA = ("clean", "crunch", "high-gain")   # drawn in this order
HELD_OUT_PER_STRATUM = 2         # 6 of 17 bands, about a third
N_FOLDS = 4                      # K3-style: shuffle sorted bands, deal round-robin
JUDGE_LATENCY = 52               # judge lag = waveform lag - 52 (di-recovery-plan.md)
MIN_WAVEFORM_WINDOWS = 3         # passing windows of the waveform same-take test
CLIP_RUNS = 10                   # the catalogue's "DI clips" line (>= 10 flat-topped runs)
ONSET_CLEAR = 0.9                # onset cross-check counts when runner-up < 0.9
ONSET_AGREE_SAMPLES = 48         # ... and agrees within 1 ms at 48 kHz
# Bands already in an earlier set's development side: never held out in set 3.
DEVELOPMENT_ONLY = {"Eat The Feeder": "its 'Today's The Day' is a set-2 development session"}
# A band already in K3's folds (sets 1-2) keeps its K3 fold, so that the fold-k network
# never sees its DIs from either set (learn.train.k3_folds: Eat The Feeder -> 2).
PINNED_FOLDS = {"Eat The Feeder": 2}
EFFECTS_OR_BLEED = "effects, bleed or noise"
CLASS_ORDER = {c: i for i, c in enumerate(STRATA)}


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tone(part: str) -> str:
    return part[:-2] if part.endswith("DT") else part


def crop_records(crops: pathlib.Path):
    out = {}
    for rec_path in sorted(crops.glob("*/record.json")):
        rec = json.loads(rec_path.read_text())
        out[(rec["session_key"], rec["part"])] = (rec_path.parent.name, rec)
    return out


def exclusion_reasons(part, crop):
    """Why a usable catalogue part is left out of set 3 (empty when kept)."""
    why = []
    wf = part["waveform"]
    passing = round(wf["windows"] * wf["in_step_fraction"])
    if not part["supp_same_take"]:
        why.append("fails the waveform same-take test")
    elif passing < MIN_WAVEFORM_WINDOWS:
        why.append(f"waveform same-take test passes on {passing} window(s), fewer than 3")
    if part["di_clip"]["runs_ge3"] >= CLIP_RUNS:
        why.append(f"DI clips ({part['di_clip']['runs_ge3']} flat-topped runs at full scale)")
    if any(f.startswith("lag ambiguous") for f in part["flags"]):
        why.append(f"two lag clusters (only {wf['precise_fraction']:.0%} of windows within "
                   "0.25 ms of the median)")
    if crop is None:
        why.append("no crop")
    return why


def marks(part):
    m = []
    if any(EFFECTS_OR_BLEED in r for r in part["gain_confidence_reasons"]):
        m.append("effects_or_bleed")
    if 0 < part["di_clip"]["runs_ge3"] < CLIP_RUNS:
        m.append("di_touches_full_scale")
    if any("ms after the DI" in f for f in part["flags"]):
        m.append("late_amp_track")
    if any(f.startswith("amp track earlier") for f in part["flags"]):
        m.append("amp_earlier_than_di")
    return m


def band_stratum(kept_parts):
    """The most common session-level gain class over the band's tones (a double counts
    with its original); a tie goes to the cleaner class, the scarcer one in set 3."""
    tones = {}
    for p in kept_parts:
        tones.setdefault((p["session_key"], _tone(p["part"])), p["gain_class"])
    counts = collections.Counter(tones.values())
    return min(counts, key=lambda c: (-counts[c], CLASS_ORDER[c]))


def draw(strata):
    """Held-out bands per stratum, then K3-style folds over the development bands."""
    rng = random.Random(SEED)
    held = {}
    for s in STRATA:
        eligible = sorted(b for b, c in strata.items() if c == s and b not in DEVELOPMENT_ONLY)
        held[s] = sorted(rng.sample(eligible, min(HELD_OUT_PER_STRATUM, len(eligible))))
    held_bands = {b for bs in held.values() for b in bs}
    dev = sorted(b for b in strata if b not in held_bands and b not in PINNED_FOLDS)
    rng.shuffle(dev)
    # Deal round-robin, the pinned bands' folds last, so those folds get fewer drawn bands.
    pinned = sorted(set(PINNED_FOLDS.values()))
    order = [f for f in range(N_FOLDS) if f not in pinned] + pinned
    fold_of = {b: order[i % N_FOLDS] for i, b in enumerate(dev)}
    fold_of.update({b: f for b, f in PINNED_FOLDS.items() if b in strata})
    return held, dict(sorted(fold_of.items()))


def build(catalog_path: pathlib.Path, crops: pathlib.Path):
    cat = json.loads(catalog_path.read_text())
    recs = crop_records(crops)
    kept, excluded = [], []
    for s in cat["sessions"]:
        for p in s["parts"]:
            if not p.get("usable_rule"):
                continue
            crop = recs.get((s["key"], p["part"]))
            why = exclusion_reasons(p, crop[1] if crop else None)
            base = {"session_key": s["key"], "band": s["group"], "song": s["song"],
                    "part": p["part"], "source": s["source"]}
            if why:
                excluded.append({**base, "slug": crop[0] if crop else None, "reasons": why})
                continue
            slug, rec = crop
            wf = p["waveform"]
            lag = rec["lag"]
            onset_clear = lag["onset_runner_up"] is not None and lag["onset_runner_up"] < ONSET_CLEAR
            onset = ("unclear" if not onset_clear else
                     "agrees" if abs(lag["onset_lag_samples"] - lag["lag_samples"]) <= ONSET_AGREE_SAMPLES
                     else "disagrees")
            kept.append({
                **base, "slug": slug, "tone": _tone(p["part"]),
                "gain_class": p["gain_class"], "gain_class_crop": rec["gain_class_crop"],
                "gain_confidence": p["gain_confidence"],
                "gain_confidence_reasons": p["gain_confidence_reasons"],
                "clean_vs_driven": p["clean_vs_driven"],
                "lag_samples": lag["lag_samples"],
                "judge_lag_samples": lag["lag_samples"] - JUDGE_LATENCY,
                "lag_samples_native": lag["lag_samples_native"], "native_rate": lag["native_rate"],
                "polarity": lag["polarity"],
                "pairing_test": "envelope+waveform" if p["repo_usable"] else "waveform",
                "waveform": {"windows": wf["windows"],
                             "passing_windows": round(wf["windows"] * wf["in_step_fraction"]),
                             "median_peak_to_sidelobe": wf["median_peak_to_sidelobe"],
                             "precise_fraction": wf["precise_fraction"]},
                "onset_check": {"result": onset, "onset_lag_samples": lag["onset_lag_samples"],
                                "runner_up": None if lag["onset_runner_up"] is None
                                else round(lag["onset_runner_up"], 3)},
                "marks": marks(p), "catalog_flags": p["flags"],
                "licence": s["source"],
                "crop": {"excerpt_start_s": rec["excerpt_start_s"],
                         "di_sha256": rec["outputs"]["di"]["sha256"],
                         "reference_sha256": rec["outputs"]["reference"]["sha256"]},
            })

    by_band = collections.defaultdict(list)
    for p in kept:
        by_band[p["band"]].append(p)
    strata = {b: band_stratum(ps) for b, ps in sorted(by_band.items())}
    held, fold_of = draw(strata)
    held_bands = {b for bs in held.values() for b in bs}
    for p in kept:
        p["split"] = "held_out" if p["band"] in held_bands else "development"
        p["fold"] = fold_of.get(p["band"])
        p["band_stratum"] = strata[p["band"]]

    sessions = []
    for s in cat["sessions"]:
        band = s["group"]
        split = "held_out" if band in held_bands else "development"
        sessions.append({"key": s["key"], "band": band, "song": s["song"], "source": s["source"],
                         "path": s["path"], "archive_sha256": s["archive_sha256"],
                         "split": split, "fold": fold_of.get(band),
                         "kept_parts": sum(1 for p in kept if p["session_key"] == s["key"])})

    def count(rows, key):
        return dict(sorted(collections.Counter(key(r) for r in rows).items(), key=str))

    order = ["slug", "band", "song", "part", "tone", "split", "fold", "band_stratum"]
    kept = [{**{k: p[k] for k in order}, **{k: v for k, v in p.items() if k not in order}}
            for p in sorted(kept, key=lambda p: (p["split"], p["band"], p["slug"]))]
    return {
        "schema": "validation-set3-1",
        "declared": DECLARED,
        "catalog": {"path": "~/ndsp-presets/references/datasets-set3/catalog.json",
                    "sha256": _sha(catalog_path), "schema": cat["schema"]},
        "crops_root": "~/ndsp-presets/references/validation-crops-set3",
        "seed": SEED,
        "rules": {
            "same_take": "waveform test (catalog rules.supplementary_pairing), adopted for set 3 "
                         "as a stated departure from the envelope test",
            "min_passing_waveform_windows": MIN_WAVEFORM_WINDOWS,
            "clipped_di_runs": CLIP_RUNS,
            "two_lag_clusters": "catalogue flag 'lag ambiguous'",
            "development_only_bands": DEVELOPMENT_ONLY,
            "band_stratum": "most common session-level gain class over the band's tones; "
                            "ties to the cleaner class",
            "held_out_draw": f"rng = random.Random({SEED}); for each stratum in {list(STRATA)}: "
                             f"sorted(rng.sample(sorted(eligible bands), {HELD_OUT_PER_STRATUM}))",
            "pinned_folds": PINNED_FOLDS,
            "fold_draw": "then dev = sorted(development bands not pinned); rng.shuffle(dev); "
                         "order = [unpinned folds ascending] + [pinned folds]; "
                         f"fold = order[index % {N_FOLDS}]; pinned bands keep their K3 fold",
            "judge_lag": f"lag_samples - {JUDGE_LATENCY} (48 kHz)",
            "lag_sign": cat["rules"]["lag_sign"],
        },
        "band_strata": strata,
        "held_out_draw": held,
        "held_out_bands": sorted(held_bands),
        "folds": {str(f): sorted(b for b, x in fold_of.items() if x == f) for f in range(N_FOLDS)},
        "licences": cat["licences"],
        "telefunken_attribution": "All audio files have been engineered and recorded by "
                                  "TELEFUNKEN Elektroakustik and are presented for educational "
                                  "and demonstrational purposes only.",
        "not_obtained": {"reason": cat["not_obtained"]["cloudflare_challenge"],
                         "count": len(cat["not_obtained"]["heavy_sessions"]),
                         "sessions": cat["not_obtained"]["heavy_sessions"]},
        "counts": {
            "catalogue_usable": len(kept) + len(excluded), "excluded": len(excluded),
            "kept": len(kept),
            "by_split": count(kept, lambda p: p["split"]),
            "by_split_tones": count({(p["session_key"], p["tone"]): p for p in kept}.values(),
                                    lambda p: p["split"]),
            "by_fold": count([p for p in kept if p["fold"] is not None], lambda p: p["fold"]),
            "by_split_gain_class": count(kept, lambda p: f"{p['split']}/{p['gain_class']}"),
            "by_fold_gain_class": count([p for p in kept if p["fold"] is not None],
                                        lambda p: f"{p['fold']}/{p['gain_class']}"),
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
    ap.add_argument("--catalog", type=pathlib.Path, default=home / "datasets-set3" / "catalog.json")
    ap.add_argument("--crops", type=pathlib.Path, default=home / "validation-crops-set3")
    ap.add_argument("--json", type=pathlib.Path, required=True)
    args = ap.parse_args()
    out = build(args.catalog.expanduser(), args.crops.expanduser())
    args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))
    print("held out:", out["held_out_bands"])
    print("folds:", json.dumps(out["folds"]))


if __name__ == "__main__":
    main()
