#!/usr/bin/env python3
"""Declare set 5 (fresh held-out validation material): crops, kept parts and exclusions.

    # 1. cut the crop-rule-2 crops (reads audio; DI <-> amp cross-correlation and the
    #    set-3 gain classifier only)
    .venv/bin/python research/validation_set5.py crops
    # 2. write the declaration (reads JSON only)
    .venv/bin/python research/validation_set5.py declare --json docs/validation-set5.json

`declare` reads only the inventory (`~/ndsp-presets/references/datasets-set5/inventory.json`)
and the crop records (`validation-crops-set5/<slug>/record.json`). It opens no audio,
starts no plugin and scores nothing. The rules are set 4's (`docs/validation-set4.md`),
through set 3's exclusion and mark functions, with every band held out (no draw, no
folds). Set 5 adds a scope mark: clean and crunch parts are in scope, high-gain parts
are report-only (`docs/validation-set5.md`).

`crops` cuts a 10-s crop by crop rule 2 (`docs/validation-datasets.md`) for every part
whose reference passed a same-take test, as set 4's `build_crops.py` did, but with its
own loader: FLAC re-host files are not accepted by `build_validation_crops.build`, and
six Cambridge sessions were unpacked guitar-only, so their crops are DI and reference
only (no mix or backing). It never re-measures a lag: the declared lag is the
inventory's waveform lag. It writes nothing over an existing crop.
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
HOME = pathlib.Path.home() / "ndsp-presets" / "references"
ROOT = HOME / "datasets-set5"
CROPS = HOME / "validation-crops-set5"
INVENTORY = ROOT / "inventory.json"
FAILED = "crops_failed.json"      # parts whose crop could not be cut, with the reason
# gainmeasure.py and classify.py: set 3's, byte-identical in set 4's tools (set 4's doc)
GAIN_TOOLS = HOME / "datasets-set4" / "_tools"

IN_SCOPE_CLASSES = ("clean", "crunch")       # high-gain parts are report-only
HF_SOURCE = "hf-rawstems"
SAMPLE_RATE = 48000
ONSET_SPAN = int(0.015 * SAMPLE_RATE)
# Reasons, recorded by the inventory, that make a part's reference not its own take: no
# crop is cut for these (set 4: such parts had no usable_rule).
NOT_ITS_OWN = ("reference is a modeller track", "its only passing amp tracks are not its own")


# --- names ---------------------------------------------------------------------------

def source_of(s) -> str:
    return "cambridge" if s["route"] in ("direct", "wayback") else HF_SOURCE


def session_key(s) -> str:
    if source_of(s) == "cambridge":
        return "cambridge/" + s["url"].rsplit("/", 1)[1].removesuffix(".zip")
    return f"{HF_SOURCE}/{s['song_dir'].split('/', 1)[1]}"


def session_dir(s) -> str:
    """The session's audio directory, relative to the set-5 root."""
    dirs = {str(pathlib.PurePosixPath(p["di"]).parent) for p in s["parts"]}
    assert len(dirs) == 1, (s["folder"], dirs)
    return f"{s['folder']}/{dirs.pop()}"


def slugify(*parts) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-") for p in parts)


def slug_of(s, p) -> str:
    return slugify(source_of(s), s["song"], p["part"])


def _base(name: str | None) -> str | None:
    return None if name is None else pathlib.PurePosixPath(name).name


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _passing_pair(p):
    return next((x for x in p.get("pairs", []) if x["amp"] == p.get("reference")), None)


def croppable(p) -> bool:
    """Set 4's usable_rule: the reference passes a same-take test (waveform, or envelope
    not at waveform null) and is the part's own amp track, not a modeller."""
    pair = _passing_pair(p)
    if pair is None or p["status"] == "fails":
        return False
    if any(r.startswith(NOT_ITS_OWN) for r in p.get("reasons", [])):
        return False
    return bool(pair["waveform_pass"] or (pair["envelope_pass"] and not pair["waveform_null"]))


def _vs3_part(p):
    """The inventory part in the shape set 3's exclusion and mark functions read."""
    pair = _passing_pair(p)
    wf = pair["waveform"]
    return {"waveform": wf, "supp_same_take": pair["waveform_pass"], "di_clip": p["di_clip"],
            "flags": p["flags"], "gain_confidence_reasons": p["gain_confidence_reasons"]}


# --- crops (audio) -------------------------------------------------------------------

def _source_check(inv_session, rel: str, path: pathlib.Path, archives, hf_files) -> dict:
    """Check a source file against what was recorded when it was fetched: the LFS
    SHA-256 for a re-host file, the archive member's byte length for a Cambridge file
    (the archive was hashed, then deleted). Raises on a mismatch."""
    sha = _sha(path)
    folder = inv_session["folder"]
    if source_of(inv_session) == HF_SOURCE:
        recorded = {f["file"]: f["sha256"] for f in inv_session["files_fetched"]}
        name = path.name
        if name not in recorded:   # a non-guitar file listed only in the song directory listing
            listing = {pathlib.PurePosixPath(x[0]).name: x[2] for x in hf_files[folder]["all_files_in_song_dir"]}
            recorded = listing
        if recorded.get(name) != sha:
            raise ValueError(f"{folder}/{rel}: SHA-256 differs from the recorded LFS hash")
        return {"sha256": sha, "checked_against": "Hugging Face LFS SHA-256 at the pinned revision"}
    members = dict(tuple(m) for m in archives[folder]["members"])
    size = path.stat().st_size
    if members.get(rel) != size:
        raise ValueError(f"{folder}/{rel}: {size} bytes, archive member {members.get(rel)}")
    return {"sha256": sha, "checked_against": "archive member length (archive SHA-256 in the inventory)"}


def _mix_plan(s, parts_to_crop):
    """Set 4's mix rule, for a session unpacked in full: every session WAV but the guitar
    DIs, the cropped parts' alternate amp tracks, rendered mixes and click tracks, and
    other DI-named guitar tracks. None when the session was unpacked guitar-only."""
    import validation_datasets as vd

    if source_of(s) != "cambridge" or s.get("unpacked") != "all":
        return None
    d = ROOT / session_dir(s)
    wavs = sorted(f.name for f in d.glob("*.wav") if not f.name.startswith("._"))
    dis = {_base(x) for x in s["di_tracks"]}
    alternates = {_base(a) for p in parts_to_crop for a in p.get("alternates", [])}
    amps = {_base(p["reference"]) for p in parts_to_crop}
    mix = [w for w in wavs if w not in dis | alternates
           and not any(r.search(pathlib.PurePosixPath(w).stem) for r in (vd.RENDERED_MIX, vd.CLICK_TRACK))
           and not (w not in amps and vd.GUITAR_DI.search(pathlib.PurePosixPath(w).stem))]
    vocals = [w for w in mix if vd.VOCAL_TRACK.search(pathlib.PurePosixPath(w).stem)]
    return mix, vocals


def _finite(x):
    """NaN (a gain measure with no window, e.g. crest1s on a short part) as JSON null."""
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_finite(v) for v in x]
    return None if isinstance(x, float) and x != x else x


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
    archives = json.loads((ROOT / "_tools" / "archives.json").read_text())
    hf_files = json.loads((ROOT / "_tools" / "hf_files.json").read_text())
    made = []
    failed_path = crops / FAILED
    failed = json.loads(failed_path.read_text()) if failed_path.exists() else {}
    for s in inv["sessions"]:
        todo = [p for p in s["parts"] if croppable(p)]
        if not todo:
            continue
        sdir = session_dir(s)
        plan = _mix_plan(s, [p for p in s["parts"] if p["status"] == "passes"])
        for p in todo:
            slug = slug_of(s, p)
            out = crops / slug
            if out.exists() or f"{session_key(s)}/{p['part']}" in failed:
                continue
            checked = {}

            def load(name: str):
                rel = f"{pathlib.PurePosixPath(p['di']).parent}/{name}"
                path = ROOT / sdir / name
                checked[name] = _source_check(s, rel, path, archives, hf_files)["sha256"]
                return io.load(path).mono().astype(np.float32)

            di = load(_base(p["di"]))
            length = len(di)
            reference = bvc._fit(load(_base(p["reference"])), length)
            try:
                start, end, lufs, activity = bvc._window_by_di(di, reference, SAMPLE_RATE)
            except ValueError as e:   # set 4: the part is left without a crop, and so excluded
                failed[f"{session_key(s)}/{p['part']}"] = {"slug": slug, "crop_failed": str(e)}
                print(slug, "CROP FAILED", e, flush=True)
                continue
            outputs = {"di": di[start:end], "reference": reference[start:end]}
            included, vocals = [], []
            if plan is not None:
                mix_names, vocals = plan
                own = {_base(p["reference"]), *(_base(a) for a in p.get("alternates", []))}
                mix = np.zeros(end - start, dtype=np.float64)
                own_amps, singing = np.zeros_like(mix), np.zeros_like(mix)
                for name in mix_names:
                    x = reference if name == _base(p["reference"]) else bvc._fit(load(name), length)
                    c = x[start:end].astype(np.float64)
                    mix += c
                    if name in own:
                        own_amps += c
                    if name in vocals:
                        singing += c
                    included.append(name)
                backing = mix - own_amps
                outputs.update(mix=mix.astype(np.float32), backing=backing.astype(np.float32))
                if vocals:
                    outputs["mix_instrumental"] = (mix - singing).astype(np.float32)
                    outputs["backing_instrumental"] = (backing - singing).astype(np.float32)

            pair = _passing_pair(p)
            sr_native = p["sample_rate"]
            lag_native = p["lag_samples_native"] if pair["waveform_pass"] else None
            lag48 = int(round(lag_native * SAMPLE_RATE / sr_native)) if lag_native is not None else None
            try:
                onset, runner = rpl.onset_lag(outputs["di"].astype(np.float64),
                                              outputs["reference"].astype(np.float64),
                                              lag48 if lag48 is not None else int(round(p["lag_ms"] * 48)),
                                              ONSET_SPAN)
            except Exception as e:  # noqa: BLE001
                onset, runner = f"error: {e}", None
            cls, conf, why, split = classify(p["gain_measures"])
            crop_m = gainmeasure.measures(outputs["reference"].astype(np.float64),
                                          outputs["di"].astype(np.float64), SAMPLE_RATE, lag48 or 0)
            crop_cls = classify(crop_m)[0] if crop_m else None
            lufs_by_role = {}
            for role in ("di", "reference", "mix", "mix_instrumental"):
                if role in outputs:
                    lufs_by_role[role] = io.loudness_lufs(io.from_samples(outputs[role], SAMPLE_RATE))
            rec = {
                "schema": "validation-crops-2", "excerpt_rule": "di-activity", "di_activity": activity,
                "inventory": {"path": str(inventory), "sha256": _sha(inventory)},
                "built_with": "research/validation_set5.py crops (build_validation_crops._window_by_di, "
                              "crop rule 2)",
                "source": source_of(s), "song": s["song"], "part": p["part"], "split": SPLIT,
                "sample_rate": SAMPLE_RATE, "channels": 1, "session_frames": length,
                "excerpt_start_frame": start, "excerpt_end_frame": end,
                "excerpt_start_s": start / SAMPLE_RATE, "excerpt_duration_s": 10.0, "reference_lufs": lufs,
                "policy": "mono channel mean; first-sample alignment; session length from DI; "
                          "short stems zero-padded and long stems cut; unity WAV-stem sum; "
                          "no normalization or limiting; float32 WAV",
                "mix_rule": ("set 4's: every session WAV but the guitar DIs, kept parts' alternate amp "
                             "tracks, rendered mixes, click tracks and other DI-named guitar tracks"
                             if plan is not None else
                             "none: the session's mix tracks are not on disk (unpacked guitar-only, or a "
                             "re-host fetched guitar-only); di and reference only"),
                "mix_absent": plan is None,
                "included_mix_tracks": included, "vocal_tracks": sorted(vocals if plan else []),
                "excluded_guitar_dis": sorted(_base(x) for x in s.get("di_tracks") or [q["di"] for q in s["parts"]]),
                "removed_own_amp_tracks": sorted({_base(p["reference"]), *(_base(a) for a in p.get("alternates", []))}),
                "verified_source_sha256": checked, "outputs": {},
                "set": 5, "session_key": session_key(s), "artist": s["band"], "group": s["band"],
                "genre": s["genre_by_library"], "route": s["route"],
                "pairing": {"reference": _base(p["reference"]), "di": _base(p["di"]),
                            "same_take_rule": p["same_take_rule"], "envelope_corr": pair["envelope_corr"],
                            "envelope_lag_ms": pair["envelope_lag_ms"],
                            "windowed": pair["envelope_windowed"], "waveform": pair["waveform"],
                            "waveform_same_take": pair["waveform_pass"]},
                "lag": {"lag_samples": lag48,
                        "lag_samples_note": "waveform (GCC-PHAT, 80 Hz-4 kHz) median lag over the session's 20-s "
                                            "windows (inventory), converted to 48 kHz; positive when the amp track "
                                            "is later; not applied",
                        "judge_lag_samples": None if lag48 is None else lag48 - vs3.JUDGE_LATENCY,
                        "lag_samples_native": lag_native, "native_rate": sr_native,
                        "polarity": p["polarity"] if pair["waveform_pass"] else None,
                        "waveform_windows": p["waveform_windows"], "lag_ms_envelope": pair["envelope_lag_ms"],
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
            with tempfile.TemporaryDirectory(prefix="set5-crop-", dir=crops) as staged:
                stage = pathlib.Path(staged)
                for role, x in outputs.items():
                    f = stage / f"{role}.wav"
                    sf.write(f, x, SAMPLE_RATE, subtype="FLOAT")
                    rec["outputs"][role] = {"path": str(out / f.name), "sha256": _sha(f), "frames": len(x)}
                (stage / "record.json").write_text(json.dumps(rec, indent=2, allow_nan=False) + "\n")
                os.rename(stage, out)
            made.append(slug)
            print(slug, rec["excerpt_start_s"], round(activity, 3), lag48, onset, runner, cls, crop_cls,
                  "mix" if plan else "no-mix", flush=True)
    if failed:
        crops.mkdir(parents=True, exist_ok=True)
        failed_path.write_text(json.dumps(failed, indent=1, sort_keys=True) + "\n")
    return made


# --- the declaration (JSON only) -----------------------------------------------------

def _excluded_reason(p) -> list[str]:
    if p["status"] == "fails":
        return list(p.get("reasons") or ["no amp track passes the same-take tests"])
    return list(p.get("reasons") or [])


def build(inventory: pathlib.Path = INVENTORY, crops: pathlib.Path = CROPS):
    inv = json.loads(inventory.read_text())
    recs = vs3.crop_records(crops) if crops.exists() else {}
    failed = json.loads((crops / FAILED).read_text()) if (crops / FAILED).exists() else {}
    kept, excluded, unpaired = [], [], []
    for s in inv["sessions"]:
        key, source = session_key(s), source_of(s)
        base = {"session_key": key, "band": s["band"], "song": s["song"], "source": source}
        used = set()
        for p in s["parts"]:
            used |= {p.get("reference"), *p.get("alternates", []), *p.get("name_declared_amps", [])}
            crop = recs.get((key, p["part"]))
            if p["status"] != "passes":
                excluded.append({**base, "part": p["part"], "slug": crop[0] if crop else None,
                                 "crop_record_sha256": crop[2] if crop else None,
                                 "reasons": _excluded_reason(p)})
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
            pair, lag = _passing_pair(p), rec["lag"]
            wf = pair["waveform"]
            onset_clear = lag["onset_runner_up"] is not None and lag["onset_runner_up"] < vs3.ONSET_CLEAR
            onset = ("unclear" if not onset_clear else
                     "agrees" if abs(lag["onset_lag_samples"] - lag["lag_samples"]) <= vs3.ONSET_AGREE_SAMPLES
                     else "disagrees")
            kept.append({
                "slug": slug, "band": s["band"], "song": s["song"], "part": p["part"],
                "tone": vs3._tone(p["part"]), "split": SPLIT, "fold": None,
                "scope": "in_scope" if p["gain_class"] in IN_SCOPE_CLASSES else "report_only",
                "session_key": key, "source": source, "route": s["route"],
                "publisher_original": s["publisher_original"],
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
                "reference": _base(p["reference"]), "alternates": [_base(a) for a in p.get("alternates", [])],
                "di": _base(p["di"]),
                "name_declared_reference": pair["name_declared"],
                "waveform": {"windows": wf["windows"],
                             "passing_windows": round(wf["windows"] * wf["in_step_fraction"]),
                             "median_peak_to_sidelobe": wf["median_peak_to_sidelobe"],
                             "precise_fraction": wf["precise_fraction"]},
                "evidence": {"pairs": f"_tools/pairs/{s['folder']}.json",
                             "inventory": f"inventory.json: sessions[folder={s['folder']!r}].parts[part={p['part']!r}]"},
                "onset_check": {"result": onset, "onset_lag_samples": lag["onset_lag_samples"],
                                "runner_up": None if lag["onset_runner_up"] is None
                                else round(lag["onset_runner_up"], 3)},
                "marks": vs3.marks(_vs3_part(p)) + (["polarity_inverted"] if lag["polarity"] == -1 else [])
                         + ([] if pair["name_declared"] else ["reference_not_name_declared"])
                         + (["crop_di_plays_under_half"] if rec["di_activity"] < 0.5 else []),
                "inventory_flags": p["flags"],
                "licence": source,
                "crop": {"excerpt_start_s": rec["excerpt_start_s"],
                         "di_activity": round(rec["di_activity"], 4),
                         "mix_absent": rec["mix_absent"],
                         "di_sha256": rec["outputs"]["di"]["sha256"],
                         "reference_sha256": rec["outputs"]["reference"]["sha256"],
                         "record_sha256": rec_sha},
            })
        for amp in s.get("amp_candidates") or []:
            if amp not in used:
                unpaired.append({"session": key, "track": _base(amp),
                                 "reason": "guitar amp/microphone track with no DI"})

    sessions = []
    for s in inv["sessions"]:
        key = session_key(s)
        row = {"key": key, "band": s["band"], "song": s["song"], "source": source_of(s),
               "path": session_dir(s), "route": s["route"], "genre_by_library": s["genre_by_library"],
               "publisher_original": s["publisher_original"]}
        if source_of(s) == "cambridge":
            row.update(url=s["url"], archive_sha256=s["archive_sha256"], archive_bytes=s["archive_bytes"],
                       wayback_capture=(re.search(r"/web/(\d+)id_/", s["url"]).group(1)
                                        if s["route"] == "wayback" else None),
                       unpacked=s["unpacked"], mix_on_disk=s["unpacked"] == "all")
        else:
            row.update(hf_repo=s["hf_repo"], revision=s["revision"], song_dir=s["song_dir"],
                       files_fetched=[{"file": f["file"], "sha256": f["sha256"]} for f in s["files_fetched"]],
                       mix_on_disk=False)
        row.update(licence_extra=s.get("licence_flag"), split=SPLIT, fold=None,
                   kept_parts=sum(1 for p in kept if p["session_key"] == key),
                   dis=[{"part": p["part"], "di": f"{s['folder']}/{p['di']}",
                         "di_clip_runs": (p.get("di_clip") or {}).get("runs_ge3"),
                         "clipped": ((p.get("di_clip") or {}).get("runs_ge3") or 0) >= vs3.CLIP_RUNS}
                        for p in s["parts"]])
        sessions.append(row)

    def count(rows, key):
        return dict(sorted(collections.Counter(key(r) for r in rows).items(), key=str))

    tones = list({(p["session_key"], p["tone"]): p for p in kept}.values())
    kept.sort(key=lambda p: (p["band"], p["slug"]))
    by_band_tones = collections.defaultdict(collections.Counter)
    for t in tones:
        by_band_tones[t["band"]][t["gain_class"]] += 1
    order = {c: i for i, c in enumerate(vs3.STRATA)}
    # the most common class over a band's tones; a tie goes to the cleaner class (set 3)
    strata = {b: min(c, key=lambda k: (-c[k], order[k])) for b, c in sorted(by_band_tones.items())}
    tools = {f: _sha(GAIN_TOOLS / f) for f in ("classify.py", "gainmeasure.py") if (GAIN_TOOLS / f).exists()}
    return {
        "schema": "validation-set5-1",
        "declared": DECLARED,
        "amendments": [],
        "precedent": "docs/validation-set4.md (rules, crop rule 2, judge lag); the inventory "
                     "(tmp/set5-inventory.md on the main checkout) came first, as set 4's plan did",
        "inventory": {"path": "~/ndsp-presets/references/datasets-set5/inventory.json",
                      "sha256": vs3._sha(inventory), "schema": inv["schema"]},
        "root": "~/ndsp-presets/references/datasets-set5",
        "crops_root": "~/ndsp-presets/references/validation-crops-set5",
        "gain_tools_sha256": tools,
        "rules": {
            "same_take": "waveform test (>= 80% of 20-s windows in step, median peak-to-sidelobe >= 2.0), "
                         "as sets 3 and 4; every DI tested against every electric-guitar track of its session",
            "min_passing_waveform_windows": vs3.MIN_WAVEFORM_WINDOWS,
            "clipped_di_runs": vs3.CLIP_RUNS,
            "two_lag_clusters": "inventory flag 'lag ambiguous'",
            "other_exclusions": "a modeller (Pod/GR4) as the reference; an amp track that belongs to another DI",
            "reference_choice": "set 4's AMP_PREFERENCE among the amp tracks the names declare; else the "
                                "passing track",
            "split": "every band held out: no draw, no folds",
            "scope": {"in_scope": list(IN_SCOPE_CLASSES), "report_only": ["high-gain"],
                      "rule": "a part's session-level gain_class: clean and crunch parts are in scope; "
                              "high-gain parts are reported, never counted in a set-5 decision "
                              "(docs/ROADMAP scope: no heavy metal)"},
            "crop": "crop rule 2 ('di-activity'), 10 s, 48 kHz mono, docs/validation-datasets.md",
            "judge_lag": f"lag_samples - {vs3.JUDGE_LATENCY} (48 kHz)",
            "lag_sign": "positive when the amp track is later than the DI",
            "band_weighting": "recommended as set 3's amendment (4): each band's parts weigh 1/n; "
                              "a confirmation plan adopts or overrides it explicitly",
        },
        "held_out_bands": sorted({s["band"] for s in sessions}),
        "band_strata": strata,
        "licences": {
            "cambridge": "Cambridge-MT 'Mixing Secrets' multitrack library: provided for educational purposes "
                         "only; not to be used for any commercial purpose without the express permission of the "
                         "copyright holders (each session's Readme.txt). https://cambridge-mt.com/ms/mtk/",
            HF_SOURCE: "Third-party re-host of the same library: Hugging Face dataset "
                       "kwatcharasupat/mixing-secrets-rawstems, pinned at revision "
                       "b482eb2e31aa15ff10489b3b23871a1e7a109198. Dataset card: 'strictly ... only for "
                       "non-commercial research and educational purposes'. Not the publisher's bytes: 48 kHz "
                       "stereo FLAC with identical channels, renamed, tracks trimmed to different lengths.",
        },
        "unpaired": unpaired,
        "counts": {
            "declared_parts": len(kept) + len(excluded), "excluded": len(excluded), "kept": len(kept),
            "kept_tones": len(tones),
            "in_scope": sum(p["scope"] == "in_scope" for p in kept),
            "report_only": sum(p["scope"] == "report_only" for p in kept),
            "by_band": count(kept, lambda p: p["band"]),
            "by_band_tones": count(tones, lambda p: p["band"]),
            "by_gain_class": count(kept, lambda p: p["gain_class"]),
            "by_band_gain_class": count(kept, lambda p: f"{p['band']}/{p['gain_class']}"),
            "by_gain_class_crop": count(kept, lambda p: p["gain_class_crop"]),
            "by_source": count(kept, lambda p: p["source"]),
            "mix_absent": sum(p["crop"]["mix_absent"] for p in kept),
            "onset_check": count(kept, lambda p: p["onset_check"]["result"]),
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
