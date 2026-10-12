#!/usr/bin/env python3
"""Declare set 6 (MedleyDB, fresh held-out validation material): crops, kept parts and exclusions.

    # 1. cut the crop-rule-2 crops (reads audio: the DI, its amp track and the song's mix;
    #    DI <-> amp cross-correlation and the set-3 gain classifier only)
    .venv/bin/python research/validation_set6.py crops
    # 2. write the declaration (reads JSON only)
    .venv/bin/python research/validation_set6.py declare --json docs/validation-set6.json

`declare` reads only the inventory (`~/ndsp-presets/references/datasets-medleydb/inventory.json`)
and the crop records (`validation-crops-set6/<slug>/record.json`). It opens no audio,
starts no plugin and scores nothing. The rules are set 5's (`docs/validation-set5.md`), with
one addition: MedleyDB names no DI, so the inventory infers each part's DI by a declared
DI-role rule (`docs/validation-set6.md`). Every band is held out (no draw, no folds). Clean
and crunch parts are in scope, high-gain parts report-only.

`crops` cuts a 10-s crop by crop rule 2 (`docs/validation-datasets.md`) for every part whose
reference passed the same-take and DI-role tests. Each crop has `di.wav`, `reference.wav`
and `mix.wav`: the same 10 s of the song's released MedleyDB mix (`<Song>_MIX.wav`), mono
mean at 48 kHz, for a test from a separated stem. Only the guitar raw tracks were extracted,
so there is no stem-sum mix or backing. It never re-measures a lag, and writes nothing over
an existing crop. Every source file is checked against its SHA-256 recorded after
extraction (`_tools/files.json`).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path[:0] = [str(HERE), str(REPO)]
import validation_set3 as vs3  # noqa: E402

DECLARED = "2026-10-12"
SPLIT = "held_out"
SOURCE = "medleydb"
HOME = pathlib.Path.home() / "ndsp-presets" / "references"
ROOT = HOME / "datasets-medleydb"
CROPS = HOME / "validation-crops-set6"
INVENTORY = ROOT / "inventory.json"
FILES = ROOT / "_tools" / "files.json"
FAILED = "crops_failed.json"      # parts whose crop could not be cut, with the reason
GAIN_TOOLS = HOME / "datasets-set4" / "_tools"   # set 3's classify.py / gainmeasure.py, as set 5

IN_SCOPE_CLASSES = ("clean", "crunch")       # high-gain parts are report-only
SAMPLE_RATE = 48000
ONSET_SPAN = int(0.015 * SAMPLE_RATE)
ZENODO = {"V1": {"record": "1649325", "doi": "10.5281/zenodo.1649325", "archive": "MedleyDB_V1.tar.gz"},
          "V2": {"record": "1715175", "doi": "10.5281/zenodo.1715175", "archive": "MedleyDB_V2.tar.gz"}}
METADATA_COMMIT = "537bb7bad0601fc58e4fff8404f71658b86ef60e"   # github.com/marl/medleydb
AMENDED = "2026-10-13"
# Amendment 1 (docs/validation-set6.md): no DI-role rule met its development bar, so no
# set-6 DI is established and every part is excluded. Set 6 is unusable for DI-based tests.
DI_ROLE_ESTABLISHED = False
NO_DI_ROLE = ("DI role not established: no DI-role rule met its development calibration bar "
              "(amendment 1, docs/validation-set6.md); set 6 is unusable for DI-based tests")
NOT_GUITAR = "MedleyDB labels the track 'electric bass', not guitar"
LICENCE_MD5 = "071086fd72dc543a4a680a747874bd16"   # LICENSE.txt of both Zenodo records
MUSDB = ROOT / "_tools" / "musdb18"
MUSDB_SOURCES = {
    "tracklist.csv": "https://raw.githubusercontent.com/sigsep/website/master/content/datasets/assets/tracklist.csv",
    "musdb_mus.yaml": "https://raw.githubusercontent.com/sigsep/sigsep-mus-db/master/musdb/configs/mus.yaml",
    "musdb_splits.json": "test = the 50 track names under submissions/*/test/ in github.com/sigsep/sigsep-mus-2018 "
                         "(SiSEC 2018 results); train = tracklist.csv less test",
}


# --- names ---------------------------------------------------------------------------

def session_key(s) -> str:
    return f"{SOURCE}/{s['song']}"


def slugify(*parts) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-") for p in parts)


def slug_of(s, p) -> str:
    return slugify(SOURCE, s["song"], p["part"])


def _base(name: str | None) -> str | None:
    return None if name is None else pathlib.PurePosixPath(name).name


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def croppable(p) -> bool:
    """The reference passed the waveform same-take test and the DI-role rule (every
    inventory part did; excluded ones too, as set 4/5 cut crops for them)."""
    return bool(p.get("reference")) and p["waveform"].get("windows", 0) > 0


def _vs3_part(p):
    """The inventory part in the shape set 3's exclusion and mark functions read."""
    return {"waveform": p["waveform"], "supp_same_take": True, "di_clip": p["di_clip"],
            "flags": p["flags"], "gain_confidence_reasons": p["gain_confidence_reasons"]}


def _finite(x):
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_finite(v) for v in x]
    return None if isinstance(x, float) and x != x else x


# --- crops (audio) -------------------------------------------------------------------

def cut(inventory: pathlib.Path = INVENTORY, crops: pathlib.Path = CROPS) -> list[str]:
    """Cut every croppable part's crop that does not exist yet. Returns the slugs cut."""
    import os
    import tempfile

    import numpy as np
    import soundfile as sf

    sys.path[:0] = [str(GAIN_TOOLS), str(REPO / "scripts")]
    import build_validation_crops as bvc
    import gainmeasure
    import record_part_lags as rpl
    from analysis import io
    from classify import classify

    inv = json.loads(inventory.read_text())
    recorded = json.loads(FILES.read_text())["files"]
    made = []
    failed_path = crops / FAILED
    failed = json.loads(failed_path.read_text()) if failed_path.exists() else {}
    for s in inv["sessions"]:
        todo = [p for p in s.get("parts", []) if croppable(p)]
        for p in todo:
            slug = slug_of(s, p)
            out = crops / slug
            if out.exists() or f"{session_key(s)}/{p['part']}" in failed:
                continue
            checked = {}

            def load(rel: str):
                path = ROOT / s["dir"] / rel
                key = path.relative_to(ROOT).as_posix()
                sha = _sha(path)
                if recorded.get(key, {}).get("sha256") != sha:
                    raise ValueError(f"{key}: SHA-256 differs from _tools/files.json")
                checked[pathlib.PurePosixPath(rel).name] = sha
                return io.load(path).mono().astype(np.float32)

            di = load(p["di"])
            length = len(di)
            reference = bvc._fit(load(p["reference"]), length)
            try:
                start, end, lufs, activity = bvc._window_by_di(di, reference, SAMPLE_RATE)
            except ValueError as e:   # set 4: the part is left without a crop, and so excluded
                failed[f"{session_key(s)}/{p['part']}"] = {"slug": slug, "crop_failed": str(e)}
                print(slug, "CROP FAILED", e, flush=True)
                continue
            mix = bvc._fit(load(_base(s["mix"])), length)
            outputs = {"di": di[start:end], "reference": reference[start:end], "mix": mix[start:end]}

            sr_native = p["sample_rate"]
            lag_native = p["lag_samples_native"]
            lag48 = int(round(lag_native * SAMPLE_RATE / sr_native))
            try:
                onset, runner = rpl.onset_lag(outputs["di"].astype(np.float64),
                                              outputs["reference"].astype(np.float64), lag48, ONSET_SPAN)
            except Exception as e:  # noqa: BLE001
                onset, runner = f"error: {e}", None
            cls, conf, why, split = classify(p["gain_measures"])
            crop_m = gainmeasure.measures(outputs["reference"].astype(np.float64),
                                          outputs["di"].astype(np.float64), SAMPLE_RATE, lag48)
            crop_cls = classify(crop_m)[0] if crop_m else None
            lufs_by_role = {role: io.loudness_lufs(io.from_samples(outputs[role], SAMPLE_RATE))
                            for role in ("di", "reference", "mix")}
            rec = {
                "schema": "validation-crops-2", "excerpt_rule": "di-activity", "di_activity": activity,
                "inventory": {"path": str(inventory), "sha256": _sha(inventory)},
                "built_with": "research/validation_set6.py crops (build_validation_crops._window_by_di, "
                              "crop rule 2)",
                "source": SOURCE, "song": s["song"], "part": p["part"], "split": SPLIT,
                "sample_rate": SAMPLE_RATE, "channels": 1, "session_frames": length,
                "excerpt_start_frame": start, "excerpt_end_frame": end,
                "excerpt_start_s": start / SAMPLE_RATE, "excerpt_duration_s": 10.0, "reference_lufs": lufs,
                "policy": "mono channel mean; first-sample alignment; session length from DI; "
                          "short stems zero-padded and long stems cut; no normalization or limiting; "
                          "float32 WAV; 44.1 kHz sources resampled to 48 kHz by analysis.io.load",
                "mix_rule": "the song's released MedleyDB mix (<Song>_MIX.wav), the same 10 s; it contains "
                            "the part's guitar as mixed (with effects, other guitars and every other "
                            "instrument)",
                "mix_absent": False, "mix_source": _base(s["mix"]),
                "included_mix_tracks": [], "vocal_tracks": [],
                "removed_own_amp_tracks": [],
                "verified_source_sha256": checked, "outputs": {},
                "set": 6, "session_key": session_key(s), "artist": s["band"], "group": s["band"],
                "artist_metadata": s["artist_metadata"], "genre": s["genre"], "origin": s["origin"],
                "medleydb_version_dir": s["version_dir"], "has_bleed": s["has_bleed"],
                "pairing": {"reference": _base(p["reference"]), "di": _base(p["di"]),
                            "di_inferred": True, "di_label": p["di_label"], "reference_label": p["reference_label"],
                            "same_take_rule": p["same_take_rule"], "envelope_corr": p["envelope_corr"],
                            "envelope_lag_ms": p["envelope_lag_ms"],
                            "windowed": p["envelope_windowed"], "waveform": p["waveform"],
                            "waveform_same_take": True},
                "lag": {"lag_samples": lag48,
                        "lag_samples_note": "waveform (GCC-PHAT, 80 Hz-4 kHz) median lag over the session's 20-s "
                                            "windows (inventory), converted to 48 kHz; positive when the amp track "
                                            "is later; not applied",
                        "judge_lag_samples": lag48 - vs3.JUDGE_LATENCY,
                        "lag_samples_native": lag_native, "native_rate": sr_native,
                        "polarity": p["polarity"],
                        "waveform_windows": p["waveform_windows"], "lag_ms_envelope": p["envelope_lag_ms"],
                        "onset_lag_samples": onset, "onset_runner_up": runner,
                        "onset_note": "record_part_lags.onset_lag on this crop, +/-15 ms around lag_samples; "
                                      "trust only when runner-up < 0.9"},
                "di_activity_fraction": activity, "lufs": lufs_by_role,
                "gain_class": cls, "gain_confidence": conf, "gain_confidence_reasons": why,
                "clean_vs_driven": split,
                "gain_note": "class from the whole session (set 3's classify.py); crunch vs high-gain is "
                             "uncalibrated on real songs",
                "gain_measures_crop": crop_m, "gain_class_crop": crop_cls,
                "gain_measures_whole_session": p["gain_measures"],
                "di_clip_whole_session": p["di_clip"],
            }
            rec = _finite(rec)
            crops.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="set6-crop-", dir=crops) as staged:
                stage = pathlib.Path(staged)
                for role, x in outputs.items():
                    f = stage / f"{role}.wav"
                    sf.write(f, x, SAMPLE_RATE, subtype="FLOAT")
                    rec["outputs"][role] = {"path": str(out / f.name), "sha256": _sha(f), "frames": len(x)}
                (stage / "record.json").write_text(json.dumps(rec, indent=2, allow_nan=False) + "\n")
                os.rename(stage, out)
            made.append(slug)
            print(slug, rec["excerpt_start_s"], round(activity, 3), lag48, onset, runner, cls, crop_cls, flush=True)
    if failed:
        crops.mkdir(parents=True, exist_ok=True)
        failed_path.write_text(json.dumps(failed, indent=1, sort_keys=True) + "\n")
    return made


# --- the declaration (JSON only) -----------------------------------------------------

def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def musdb18_overlap(musdb: pathlib.Path = MUSDB) -> dict:
    """{MedleyDB song: {musdb18_track, musdb18_subset, musdb18_validation}} for every song in
    MUSDB18 (and so MUSDB18-HQ), matched on the normalised "Artist - Title" / "Artist_Title"."""
    import csv
    tracks = [r["Track Name"] for r in csv.DictReader((musdb / "tracklist.csv").open())]
    test = set(json.loads((musdb / "musdb_splits.json").read_text())["test"])
    import yaml
    valid = set(yaml.safe_load((musdb / "musdb_mus.yaml").read_text())["validation_tracks"])
    return {_norm(t): {"musdb18_track": t, "musdb18_subset": "test" if t in test else "train",
                       "musdb18_validation": t in valid} for t in tracks}


def build(inventory: pathlib.Path = INVENTORY, crops: pathlib.Path = CROPS):
    inv = json.loads(inventory.read_text())
    recs = vs3.crop_records(crops) if crops.exists() else {}
    failed = json.loads((crops / FAILED).read_text()) if (crops / FAILED).exists() else {}
    kept, excluded, unpaired, role_failures = [], [], [], []
    for s in inv["sessions"]:
        key = session_key(s)
        base = {"session_key": key, "band": s["band"], "song": s["song"], "source": SOURCE}
        used = set()
        for p in s.get("parts", []):
            used |= {_base(p["di"]), _base(p["reference"]), *(_base(a) for a in p["alternates"])}
            crop = recs.get((key, p["part"]))
            extra = ([] if DI_ROLE_ESTABLISHED else [NO_DI_ROLE]) + (
                [NOT_GUITAR] if "electric bass" in (p["di_label"], p["reference_label"]) else [])
            if p["status"] != "passes" or extra:
                excluded.append({**base, "part": p["part"], "slug": crop[0] if crop else None,
                                 "crop_record_sha256": crop[2] if crop else None,
                                 "crop_status": "superseded (amendment 1): held out, not a part" if crop else None,
                                 "di_label": p["di_label"], "reference_label": p["reference_label"],
                                 "reasons": list(p["reasons"]) + extra})
                continue
            why = vs3.exclusion_reasons(_vs3_part(p), crop[1] if crop else None)
            fail = failed.get(f"{key}/{p['part']}")
            if fail:
                why = [f"no crop: crop rule 2 failed ({fail['crop_failed']})" if r == "no crop" else r
                       for r in why]
            if why:
                excluded.append({**base, "part": p["part"],
                                 "slug": crop[0] if crop else (fail or {}).get("slug"),
                                 "crop_record_sha256": crop[2] if crop else None, "reasons": why})
                continue
            slug, rec, rec_sha = crop
            lag, wf = rec["lag"], p["waveform"]
            onset_clear = lag["onset_runner_up"] is not None and lag["onset_runner_up"] < vs3.ONSET_CLEAR
            onset = ("unclear" if not onset_clear else
                     "agrees" if abs(lag["onset_lag_samples"] - lag["lag_samples"]) <= vs3.ONSET_AGREE_SAMPLES
                     else "disagrees")
            kept.append({
                "slug": slug, "band": s["band"], "song": s["song"], "part": p["part"],
                "tone": p["part"], "split": SPLIT, "fold": None,
                "scope": "in_scope" if p["gain_class"] in IN_SCOPE_CLASSES else "report_only",
                "session_key": key, "source": SOURCE, "medleydb_version_dir": s["version_dir"],
                "origin": s["origin"], "has_bleed": s["has_bleed"],
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
                "pairing_test": p["same_take_rule"],
                "reference": _base(p["reference"]), "alternates": [_base(a) for a in p["alternates"]],
                "di": _base(p["di"]), "di_inferred": True,
                "di_label": p["di_label"], "reference_label": p["reference_label"],
                "di_role": {"di_crest1s_db": p["di_cues"]["crest1s_db"],
                            "amp_crest1s_db": p["amp_cues"]["crest1s_db"],
                            "crest1s_drop_db": p["gain_measures"]["crest1s_drop_db"],
                            "hf_advantage_db": round(p["di_cues"]["hf_5_10k_vs_0_2_4k_db"]
                                                     - p["amp_cues"]["hf_5_10k_vs_0_2_4k_db"], 2),
                            "branch": "clean" if p["gain_class"] == "clean" else "driven"},
                "waveform": {"windows": wf["windows"],
                             "passing_windows": round(wf["windows"] * wf["in_step_fraction"]),
                             "median_peak_to_sidelobe": wf["median_peak_to_sidelobe"],
                             "precise_fraction": wf["precise_fraction"]},
                "evidence": {"pairs": f"_tools/pairs/{s['song']}.json",
                             "inventory": f"inventory.json: sessions[song={s['song']!r}].parts[part={p['part']!r}]"},
                "onset_check": {"result": onset, "onset_lag_samples": lag["onset_lag_samples"],
                                "runner_up": None if lag["onset_runner_up"] is None
                                else round(lag["onset_runner_up"], 3)},
                "marks": vs3.marks(_vs3_part(p)) + (["polarity_inverted"] if lag["polarity"] == -1 else [])
                         + (["has_bleed"] if s["has_bleed"] == "yes" else [])
                         + ([] if "different MedleyDB stems" not in " ".join(p["flags"]) else ["cross_stem"])
                         + (["crop_di_plays_under_half"] if rec["di_activity"] < 0.5 else []),
                "inventory_flags": p["flags"],
                "licence": SOURCE,
                "crop": {"excerpt_start_s": rec["excerpt_start_s"],
                         "di_activity": round(rec["di_activity"], 4),
                         "mix_absent": rec["mix_absent"],
                         "di_sha256": rec["outputs"]["di"]["sha256"],
                         "reference_sha256": rec["outputs"]["reference"]["sha256"],
                         "mix_sha256": rec["outputs"]["mix"]["sha256"],
                         "record_sha256": rec_sha},
            })
        for q in s.get("role_failures", []):
            role_failures.append({**base, "di_candidate": _base(q["di_candidate"]), "amp": _base(q["amp"]),
                                  "lag_samples_native": q["lag_samples_native"],
                                  "gain_class_di_to_amp": q["gain_class_di_to_amp"], "reasons": q["reasons"]})
        for t in s.get("tracks", {}):
            if t not in used:
                unpaired.append({"session": key, "track": t,
                                 "reason": "electric-guitar raw track that is neither an established DI nor "
                                           "its amp track"})

    musdb = musdb18_overlap()
    sessions = []
    for s in inv["sessions"]:
        key = session_key(s)
        m = musdb.get(_norm(s["song"]))
        sessions.append({
            "key": key, "band": s["band"], "artist_metadata": s["artist_metadata"], "song": s["song"],
            "title": s["title"], "source": SOURCE, "path": s["dir"], "medleydb_version_dir": s["version_dir"],
            "zenodo": ZENODO[s["version_dir"]], "genre": s["genre"], "origin": s["origin"],
            "producer": s["producer"], "has_bleed": s["has_bleed"], "mix": _base(s["mix"]),
            "mix_on_disk": s["song"] != "AimeeNorwich_Child",
            "status": (s["status"] if DI_ROLE_ESTABLISHED or s["status"] != "has parts" else
                       "DI candidates under the first DI-role rule; none established (amendment 1)"),
            "eg_raw_tracks": len(s.get("tracks", {})),
            "split": SPLIT, "fold": None,
            "separator_trained_on": (None if m is None else
                                     {"dataset": "MUSDB18 / MUSDB18-HQ", **m,
                                      "note": "HTDemucs (learn/, the repo's separator) was trained on "
                                              "MUSDB18-HQ's train subset; a stem-based test excludes or "
                                              "reports this song"}),
            "kept_parts": sum(1 for p in kept if p["session_key"] == key),
            "dis": [{"part": p["part"], "di": f"{s['dir']}/{p['di']}",
                     "di_clip_runs": p["di_clip"]["runs_ge3"],
                     "clipped": p["di_clip"]["runs_ge3"] >= vs3.CLIP_RUNS} for p in s.get("parts", [])]})

    def count(rows, key):
        return dict(sorted(collections.Counter(key(r) for r in rows).items(), key=str))

    kept.sort(key=lambda p: (p["band"], p["slug"]))
    by_band = collections.defaultdict(collections.Counter)
    for p in kept:
        by_band[p["band"]][p["gain_class"]] += 1
    order = {c: i for i, c in enumerate(vs3.STRATA)}
    strata = {b: min(c, key=lambda k: (-c[k], order[k])) for b, c in sorted(by_band.items())}
    in_scope_bands = collections.defaultdict(set)
    for p in kept:
        if p["scope"] == "in_scope":
            in_scope_bands[p["gain_class"]].add(p["band"])
    tools = {f: _sha(GAIN_TOOLS / f) for f in ("classify.py", "gainmeasure.py") if (GAIN_TOOLS / f).exists()}
    return {
        "schema": "validation-set6-2",
        "declared": DECLARED,
        "amendments": [{
            "number": 1, "date": AMENDED,
            "summary": "DI-role rule calibrated on development data only (sets 1-2 and set 3 development: "
                       "177 DI->amp and 66 two-mic/two-amp/DI-DI same-take pairs, 30 bands, leave-one-band-"
                       "out). No rule kept most real DIs with <= 10% false accepts on all development "
                       "negatives (first rule: 32% of DIs, 5%; driven rule: crunch 87%, high-gain 86%, "
                       "clean 14%, 12%; any clean branch: >= 41% to keep most clean DIs). Set 6 is "
                       "unusable for DI-based tests; every part is excluded; the failed rules are not "
                       "applied to MedleyDB. Steven Clark RAW_01_04 -> 01_02 is labelled electric bass.",
            "calibration": "docs/validation-set6-di-calibration.json",
            "script": "research/set6_di_role_calibration.py",
            "committed_before_application": True}],
        "use": "unusable for DI-based tests (amendment 1); a song-only use (released mixes, no DI) needs its "
               "own declaration and crop rule",
        "precedent": "docs/validation-set5.md (rules, crop rule 2, judge lag, scope); the inventory came "
                     "first, as set 5's did; MedleyDB names no DI, so a DI-role rule is added",
        "inventory": {"path": "~/ndsp-presets/references/datasets-medleydb/inventory.json",
                      "sha256": vs3._sha(inventory), "schema": inv["schema"]},
        "root": "~/ndsp-presets/references/datasets-medleydb",
        "crops_root": "~/ndsp-presets/references/validation-crops-set6",
        "gain_tools_sha256": tools,
        "rules": {
            "same_take": "waveform test (>= 80% of 20-s windows in step, median peak-to-sidelobe >= 2.0), "
                         "as sets 3-5; every pair of electric-guitar raw tracks of a song tested",
            "di_role": {"status": "no DI-role rule established (amendment 1); no set-6 DI part",
                        "first_declared": inv["di_role_rule"],
                        "calibration": "docs/validation-set6-di-calibration.json"},
            "min_passing_waveform_windows": vs3.MIN_WAVEFORM_WINDOWS,
            "clipped_di_runs": vs3.CLIP_RUNS,
            "two_lag_clusters": "inventory flag 'lag ambiguous'",
            "other_exclusions": "an amp track that is also the amp track of another DI",
            "split": "every band held out: no draw, no folds",
            "scope": {"in_scope": list(IN_SCOPE_CLASSES), "report_only": ["high-gain"],
                      "rule": "a part's session-level gain_class: clean and crunch parts are in scope; "
                              "high-gain parts are reported, never counted in a set-6 decision"},
            "crop": "crop rule 2 ('di-activity'), 10 s, 48 kHz mono, docs/validation-datasets.md; plus the "
                    "same 10 s of the song's released mix",
            "judge_lag": f"lag_samples - {vs3.JUDGE_LATENCY} (48 kHz)",
            "lag_sign": "positive when the amp track is later than the DI",
            "band_weighting": "recommended as set 3's amendment (4): each band's parts weigh 1/n; "
                              "a confirmation plan adopts or overrides it explicitly",
        },
        "held_out_bands": sorted({s["band"] for s in sessions}),
        "band_strata": strata,
        "in_scope_bands_by_class": {c: sorted(b) for c, b in sorted(in_scope_bands.items())},
        "licences": {
            SOURCE: "MedleyDB (Bittner et al., ISMIR 2014; MedleyDB 2.0, 2016): audio on Zenodo, restricted "
                    "access granted to the user for non-commercial research (records 1649325 and 1715175). "
                    "Licence: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (LICENSE-V1.txt in "
                    "the dataset root). Non-commercial research only; not republished; no audio in git.",
        },
        "licence_texts": {
            "V1": {"file": "LICENSE-V1.txt (dataset root)", "md5": LICENCE_MD5,
                   "checked": "md5 of the captured file"},
            "V2": {"file": "LICENSE.txt of Zenodo record 1715175 (not captured)", "md5": LICENCE_MD5,
                   "checked": "md5 from Zenodo's file listing, recorded while the archive was fetched; the "
                              "listing is restricted now (403)"},
            "identical": True,
            "statement": "both records ship the same CC BY-NC-SA 4.0 licence text (same md5); both record "
                         "pages state CC BY-NC-SA 4.0 (checked 2026-10-13)",
            "non_commercial_use": "validating an openly distributed, non-commercial plugin is non-commercial "
                                  "research; no MedleyDB audio or derived audio is distributed",
        },
        "provenance": {
            "archives": {v: {**z, "checksums_file": f"{z['archive']}.checksums"} for v, z in ZENODO.items()},
            "archive_checks": "each archive streamed from Zenodo, its whole-file SHA-256 and MD5 recorded "
                              "(MedleyDB_V*.tar.gz.checksums) and the MD5 checked against Zenodo's by the user; "
                              "only the mix and electric-guitar raw tracks were extracted; the archive was not kept",
            "extracted_files": "_tools/files.json: SHA-256 of every extracted file; each crop source is "
                               "checked against it",
            "metadata": f"github.com/marl/medleydb at {METADATA_COMMIT} (Metadata/*.yaml, ERRATA.md)",
            "selection": "eguitar_songs.json: songs whose metadata lists an electric-guitar raw track; 73 of "
                         "its 166 songs are in the V1/V2 audio releases",
            "musdb18_lists": {f: {"source": u, "sha256": _sha(MUSDB / f), "fetched": "2026-10-13",
                                  "copy": f"_tools/musdb18/{f}"} for f, u in MUSDB_SOURCES.items()},
        },
        "unpaired": unpaired,
        "role_failures": role_failures,
        "counts": {
            "songs": len(sessions), "declared_parts": len(kept) + len(excluded),
            "excluded": len(excluded), "kept": len(kept),
            "in_scope": sum(p["scope"] == "in_scope" for p in kept),
            "report_only": sum(p["scope"] == "report_only" for p in kept),
            "by_band": count(kept, lambda p: p["band"]),
            "by_gain_class": count(kept, lambda p: p["gain_class"]),
            "by_band_gain_class": count(kept, lambda p: f"{p['band']}/{p['gain_class']}"),
            "by_gain_class_crop": count(kept, lambda p: p["gain_class_crop"]),
            "onset_check": count(kept, lambda p: p["onset_check"]["result"]),
            "sessions_by_status": count(sessions, lambda s: s["status"]),
            "role_failures": len(role_failures),
            "separator_trained_on": sum(1 for s in sessions if s["separator_trained_on"]),
        },
        "sessions": sessions,
        "parts": kept,
        "excluded": sorted(excluded, key=lambda p: (p["band"], p["song"], p["part"])),
        "held_out_uses": [],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crops")
    c.add_argument("--inventory", type=pathlib.Path, default=INVENTORY)
    c.add_argument("--crops", type=pathlib.Path, default=CROPS)
    d = sub.add_parser("declare")
    d.add_argument("--inventory", type=pathlib.Path, default=INVENTORY)
    d.add_argument("--crops", type=pathlib.Path, default=CROPS)
    d.add_argument("--json", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.cmd == "crops":
        made = cut(args.inventory.expanduser(), args.crops.expanduser())
        print(f"{len(made)} crops cut")
        return
    out = build(args.inventory.expanduser(), args.crops.expanduser())
    args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
