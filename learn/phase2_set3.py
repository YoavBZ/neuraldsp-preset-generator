"""Phase 2 on set 3's development parts (`docs/di-recovery-plan.md`, "Phase 2 on set 3").

Three menus, one per Morgan amp: its factory presets plus its template, all with R.
Every DI is built with K3 fold 2's frozen average balance, which leaves out the only band
set 3 shares with set 2:
- **measure:** the true DI re-equalised to that average, at its own level. Scoring is on
  half B at the part's judge lag; the oracle uses half A.
- **flatref / flatstem:** the amp track / separated stem re-equalised, at −22.9 LUFS.
- **net / netstem:** the set-3 network on the amp track / stem, at −22.9 LUFS.

Choosing through a rebuilt DI uses half A against the recording it came from, with lag
−52. Renders are cached per (kind, part, amp).

    $TORCH_PY -m learn.phase2_set3 render --kinds measure flatref
    $TORCH_PY -m learn.phase2_set3 render --kinds flatstem netstem net --model .../set3.pt
    $TORCH_PY -m learn.phase2_set3 score
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import pathlib
import sys
import uuid

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

SR, LATENCY = 48000, 52
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops-set3"))
STEMS = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/set3/stems"))
CACHE = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc/cache"))
OUT = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/direc/phase2-set3"))
AVG_FOLD = 2
AMPS = ("pr12", "sw50r", "ac20")
HALF_A, HALF_B = (1.0, 5.5), (5.5, 10.0)
BAND_SETS = ("recording", "union")
REBUILT = {"flatref": "ref", "flatstem": "stem", "net": "ref", "netstem": "stem"}
MODEL = pathlib.Path("~/ndsp-presets/learn/direc/models-set3/fold2.pt").expanduser()


@dataclass(frozen=True)
class RunConfig:
    """Picklable settings carried into workers, including under macOS spawn."""

    split: str = "development"
    out: pathlib.Path | None = None
    amps: tuple[str, ...] = AMPS
    workers: int = 6
    lag_mode: str = "waveform"
    model: pathlib.Path = MODEL
    confirmation_manifest: pathlib.Path | None = None
    confirmation_sha256: str | None = None
    crops: pathlib.Path = field(default_factory=lambda: CROPS)
    stems: pathlib.Path = field(default_factory=lambda: STEMS)
    cache: pathlib.Path = field(default_factory=lambda: CACHE)

    def __post_init__(self):
        if self.split not in ("development", "held_out"):
            raise ValueError("split must be development or held_out")
        if not self.amps or len(set(self.amps)) != len(self.amps) or set(self.amps) - set(AMPS):
            raise ValueError("amps must be a nonempty, unique selection from pr12, sw50r, ac20")
        if self.workers < 1:
            raise ValueError("workers must be positive")
        if self.lag_mode not in ("waveform", "onset"):
            raise ValueError("lag_mode must be waveform or onset")
        if self.lag_mode == "onset" and self.split != "held_out":
            raise ValueError("onset sensitivity is only defined for held_out")
        object.__setattr__(self, "amps", tuple(self.amps))
        default = OUT if self.split == "development" else OUT.with_name(OUT.name + "-heldout")
        object.__setattr__(self, "out", pathlib.Path(self.out or default).expanduser().resolve())
        for name in ("model", "crops", "stems", "cache", "confirmation_manifest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, pathlib.Path(value).expanduser().resolve())
        if self.split == "held_out":
            development = OUT.expanduser().resolve()
            if (self.out == development or development in self.out.parents
                    or self.out in development.parents):
                raise ValueError("held_out output must be separate from development OUT")
            if self.confirmation_manifest is None:
                raise ValueError("held_out requires --confirmation-manifest and committed declaration validation")


def _prepare_run(config):
    """Validate before any audio, renders or output are accessed.

    The separate confirmation module owns the manifest schema and must verify the
    committed, approved declaration and all frozen inputs, raising on any mismatch.
    There is deliberately no fallback when that verifier is unavailable.
    """
    from learn import set3

    selected = set3.parts(config.split)
    parts = {p["slug"]: p for p in selected}
    if not parts or len(parts) != len(selected):
        raise ValueError("selected parts must be nonempty with unique slugs")
    manifest = None
    if config.split == "held_out":
        from learn import set3_confirmation

        # The verifier's contract uses fixed data locations. Do not consume
        # programmatic overrides that the manifest did not validate.
        for name, expected in (("cache", CACHE), ("crops", CROPS), ("stems", STEMS)):
            if getattr(config, name) != expected.expanduser().resolve():
                raise ValueError(f"confirmation must use the validated default {name}")
        manifest_digest = _manifest_digest(config)
        manifest = set3_confirmation.validate_manifest(
            config.confirmation_manifest, model=config.model, amps=config.amps,
            parts=selected, out=config.out, require_declared=True)
        if _manifest_digest(config) != manifest_digest:
            raise ValueError("confirmation manifest changed during validation")
        if not isinstance(manifest, dict):
            raise ValueError("confirmation validator must return the verified manifest")
        config = replace(config, confirmation_sha256=manifest_digest)
    _prepare_output(config)
    return config, parts, manifest


def _manifest_digest(config):
    return hashlib.sha256(config.confirmation_manifest.read_bytes()).hexdigest()


def _assert_manifest_unchanged(config):
    if config.split == "held_out":
        if config.confirmation_sha256 is None or _manifest_digest(config) != config.confirmation_sha256:
            raise ValueError("confirmation manifest changed since validation")


def _prepare_output(config):
    """Keep custom outputs split-specific and bind confirmation caches to a manifest."""
    identity = {"split": config.split}
    if config.split == "held_out":
        _assert_manifest_unchanged(config)
        identity["confirmation_manifest_sha256"] = config.confirmation_sha256
    marker = config.out / "split.json"
    for parent in config.out.parents:
        ancestor_marker = parent / "split.json"
        if ancestor_marker.is_file() and json.loads(ancestor_marker.read_text()).get("split") != config.split:
            raise ValueError("output is nested under a different split's cache")
    if marker.exists():
        if json.loads(marker.read_text()) != identity:
            raise ValueError("output split or confirmation manifest differs from existing cache")
        return
    if config.split == "held_out" and config.out.exists() and any(config.out.iterdir()):
        raise ValueError("held_out output contains an unverified cache without split.json")
    config.out.mkdir(parents=True, exist_ok=True)
    try:
        with marker.open("x") as f:
            json.dump(identity, f, sort_keys=True)
    except FileExistsError:
        if json.loads(marker.read_text()) != identity:
            raise ValueError("output split or confirmation manifest differs from existing cache")


def _require_complete(config, kind, slug, names):
    """A done marker alone cannot certify all parts, amps and candidates exist."""
    import render_preset_panel as RP

    base = config.out / kind / slug
    missing = [p for p in (base / "done", base / "di.npy") if not p.is_file()]
    for amp, candidates in names.items():
        for name in candidates:
            path = base / amp / f"{RP._slug(name)}.wav"
            if not path.is_file() and not path.with_suffix(".flac").is_file():
                missing.append(path)
    if missing:
        raise ValueError(f"incomplete {kind} renders for {slug}: {missing[0]}")
    if config.split == "held_out" and (base / "done").read_text() != config.confirmation_sha256:
        raise ValueError(f"unverified {kind} completion marker for {slug}")


def mono(path):
    """A file as mono float64. A render named `.wav` may have been stored as a
    level-normalised 24-bit `.flac` (the judge ignores level; distances agree to 1e-7)."""
    import soundfile as sf

    path = pathlib.Path(path)
    if not path.exists() and path.with_suffix(".flac").exists():
        path = path.with_suffix(".flac")
    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR, path
    return x.mean(axis=1)


def stem_usable(config):
    path = config.stems / "manifest.json"
    if not path.exists():
        return set()
    m = json.loads(path.read_text())
    return {p for p, v in m["parts"].items() if v.get("usable")}


def recording(slug, source, config):
    if source == "stem":
        return mono(config.stems / "htdemucs_6s" / slug / "instrumental_guitar.wav")
    return mono(config.crops / slug / "reference.wav")


def build_di(kind, slug, net=None, *, config):
    import numpy as np

    from learn import direc as D
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    if config.split == "held_out":
        # Frozen confirmation inputs may never be regenerated on demand.
        avg = np.load(config.cache / f"average-fold{AVG_FOLD}.npy")
    else:
        avg = D.fold_average(config.cache, AVG_FOLD)
    if kind == "measure":
        di = mono(config.crops / slug / "di.wav")
        own = smoothed_spectrum(di)
        y = eq_to(di, avg - (own - own.mean()))
        return y * math.sqrt(np.mean(di ** 2) / np.mean(y ** 2))
    rec = recording(slug, REBUILT[kind], config)
    if kind.startswith("flat"):
        own = smoothed_spectrum(rec)
        return to_lufs(eq_to(rec, avg - (own - own.mean())))
    import torch

    return to_lufs(D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64))


def menus(pack, renderer, amps=AMPS):
    import render_preset_panel as RP

    out = {}
    for amp in amps:
        m = RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY), pack, renderer)
        out[amp] = {n: RP.preset_edits(path, pack, renderer, amp, rule)
                    for n, (path, rule) in m.items() if n != "template"}
    return out


def render(kinds, model, shard=(0, 1), *, config=None):
    config = replace(config or RunConfig(), model=pathlib.Path(model))
    if config.lag_mode != "waveform":
        raise ValueError("lag-mode onset is a scoring sensitivity, not a render mode")
    if not kinds or set(kinds) - {"measure", *REBUILT}:
        raise ValueError("kinds must select measure, flatref, flatstem, net or netstem")
    if config.split == "held_out" and set(kinds) - {"measure", "flatref", "net"}:
        raise ValueError("held_out confirmation does not authorize reading stems")
    if len(shard) != 2 or not 0 <= shard[0] < shard[1]:
        raise ValueError("shard must be i/n with 0 <= i < n")
    config, parts, _ = _prepare_run(config)

    import numpy as np
    import soundfile as sf
    import torch

    import render_preset_panel as RP
    from learn import direc as D
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    usable = stem_usable(config) if any(REBUILT.get(k) == "stem" for k in kinds) else set()
    net = None
    if any(k.startswith("net") for k in kinds):
        net = D.build_model()
        net.load_state_dict(torch.load(config.model, map_location="cpu"))
        net.eval()
    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    r = PanelRenderer("morgan", process_policy="reuse")
    M = menus(pack, r, config.amps)
    PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in M.items() for n, v in m.items()}
    try:
        for slug in sorted(parts)[shard[0]::shard[1]]:
            for kind in kinds:
                if REBUILT.get(kind) == "stem" and slug not in usable:
                    if config.split == "held_out":
                        raise ValueError(f"unusable {kind} source for selected part {slug}")
                    continue
                base = config.out / kind / slug
                if (base / "done").exists():
                    if config.split == "held_out":
                        _require_complete(config, kind, slug, M)
                    continue
                base.mkdir(parents=True, exist_ok=True)
                di = build_di(kind, slug, net, config=config)
                np.save(base / "di.npy", di)
                d32 = di.astype(np.float32)
                for amp, m in M.items():
                    (base / amp).mkdir(exist_ok=True)
                    r.render(d32, {"panel": f"{amp}|template+R"})            # warm-up per amp
                    for n in m:
                        y = np.asarray(r.render(d32, {"panel": f"{amp}|{n}"}).audio, np.float64)
                        sf.write(base / amp / f"{RP._slug(n)}.flac",
                                 y * (0.99 / max(np.abs(y).max(), 1e-12)), SR, subtype="PCM_24")
                _assert_manifest_unchanged(config)
                (base / "done").write_text(config.confirmation_sha256 if config.split == "held_out" else "")
                print(slug, kind, flush=True)
    finally:
        r.close()


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance

    config, slug, lag, names, frozen_A = job
    if config.lag_mode == "onset" and frozen_A is None:
        raise ValueError("onset scoring requires frozen waveform selections")
    if config.split == "held_out":
        for kind in ("measure", "net"):
            _require_complete(config, kind, slug, names)
    ref = recording(slug, "ref", config)
    res = {}
    mdir = config.out / "measure" / slug
    mdi = np.load(mdir / "di.npy")
    for bs in BAND_SETS:
        for amp, ns in names.items():
            dB = {n: aligned_distance(ref, mono(mdir / amp / f"{RP._slug(n)}.wav"), mdi, lag=lag,
                                      render_latency=LATENCY, start_s=HALF_B[0], end_s=HALF_B[1],
                                      bands=bs).distance for n in ns}
            dA = {n: aligned_distance(ref, mono(mdir / amp / f"{RP._slug(n)}.wav"), mdi, lag=lag,
                                      render_latency=LATENCY, start_s=HALF_A[0], end_s=HALF_A[1],
                                      bands=bs).distance for n in ns}
            res[f"{bs}|{amp}|measure_B"] = dB
            res[f"{bs}|{amp}|measure_A"] = dA
            for kind, src in REBUILT.items():
                if config.split == "held_out" and src == "stem":
                    continue
                key = f"{bs}|{amp}|{kind}_A"
                if config.lag_mode == "onset":
                    if key in frozen_A:
                        res[key] = frozen_A[key]
                    continue
                d = config.out / kind / slug
                if not (d / "done").exists():
                    continue
                if config.split == "held_out":
                    _require_complete(config, kind, slug, names)
                di = np.load(d / "di.npy")
                rec = recording(slug, src, config)
                res[key] = {
                    n: aligned_distance(rec, mono(d / amp / f"{RP._slug(n)}.wav"), di, lag=-LATENCY,
                                        render_latency=LATENCY, start_s=HALF_A[0], end_s=HALF_A[1],
                                        bands=bs).distance for n in ns}
    print(slug, flush=True)
    return slug, res


def _score_lag(part, config):
    if config.lag_mode == "onset" and part.get("onset_check", {}).get("result") == "disagrees":
        lag = part["onset_check"]["onset_lag_samples"]
        if isinstance(lag, bool) or not isinstance(lag, int):
            raise ValueError(f"invalid declared onset lag for {part['slug']}")
        return lag - LATENCY
    return part["judge_lag_samples"]


def _waveform_selections(config, parts, names):
    """Sensitivity reuses the primary half-A distances, including any refusals."""
    primary = json.loads((config.out / "distances.json").read_text())
    if set(primary) != set(parts):
        raise ValueError("waveform distances must cover every declared part")
    selections = {}
    for slug, rows in primary.items():
        frozen = {}
        for bs in BAND_SETS:
            for amp, candidates in names.items():
                for kind in REBUILT:
                    key = f"{bs}|{amp}|{kind}_A"
                    if key not in rows:
                        if kind == "net":
                            raise ValueError(f"missing waveform selections: {slug}, {key}")
                        continue
                    if set(rows[key]) != set(candidates):
                        raise ValueError(f"incomplete waveform selections: {slug}, {key}")
                    frozen[key] = rows[key]
        selections[slug] = frozen
    return selections


def _atomic_json(path, value):
    _atomic_bytes(path, json.dumps(value, indent=1).encode())


def _atomic_bytes(path, data):
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _start_score_attempt(config, attempt):
    """Before validation, touch only an existing matching held-out cache identity."""
    if config.split != "held_out" or attempt:
        return
    development = OUT.expanduser().resolve()
    output = config.out.resolve()
    if output == development or development in output.parents or output in development.parents:
        return
    try:
        identity = json.loads((output / "split.json").read_text())
        digest = _manifest_digest(config)
        if identity != {"split": "held_out", "confirmation_manifest_sha256": digest}:
            return
        for parent in output.parents:
            marker = parent / "split.json"
            if marker.is_file() and json.loads(marker.read_text()).get("split") != "held_out":
                return
    except (OSError, ValueError):
        return
    history = output / "score-history" / uuid.uuid4().hex
    if not history.resolve().is_relative_to(output):
        raise ValueError("score history must remain within the held_out output")
    history.mkdir(parents=True)
    attempt.update(out=output, history=history, status={
        "attempt": history.name, "state": "pending", "lag_mode": config.lag_mode,
        "confirmation_manifest_sha256": digest,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "history": str(history.relative_to(output)),
    })
    # Move the verdict first. Historical artifacts are never current pass claims.
    for name in ("confirmation-verdict.json", "confirmation.json", "confirmation-onset.json",
                 "distances.json", "distances-onset.json", "result.json", "result-onset.json",
                 "score-attempt.json"):
        path = output / name
        if path.exists() or path.is_symlink():
            path.replace(history / name)
    _finish_score_attempt(attempt, "pending")


def _finish_score_attempt(attempt, state, error=None):
    if not attempt:
        return
    status = dict(attempt["status"], state=state)
    if state != "pending":
        status["finished_at"] = datetime.now(timezone.utc).isoformat()
    if error is not None:
        status["error"] = {"type": type(error).__name__, "message": str(error)}
    _atomic_json(attempt["history"] / "attempt.json", status)
    _atomic_json(attempt["out"] / "score-attempt.json", status)


def score(*, config=None):
    config = config or RunConfig()
    attempt = {}
    try:
        _start_score_attempt(config, attempt)
        result = _score_impl(config=config, attempt=attempt)
        _finish_score_attempt(attempt, "complete")
        return result
    except BaseException as error:
        if attempt:
            # A failure during publication must also remove any partial pass claims.
            for name in ("confirmation-verdict.json", "confirmation.json", "confirmation-onset.json"):
                path = attempt["out"] / name
                if path.exists() or path.is_symlink():
                    path.replace(attempt["history"] / ("failed-" + name))
            _finish_score_attempt(attempt, "failed", error)
        raise


def _score_impl(*, config, attempt):
    config = config or RunConfig()
    config, parts, manifest = _prepare_run(config)
    _start_score_attempt(config, attempt)
    from concurrent.futures import ProcessPoolExecutor

    from match.renderer_au import AudioUnitRenderer  # noqa: F401  (menus need a renderer object)
    from packs.loader import load_pack

    pack = load_pack("morgan")

    class Dummy:
        def _stored(self, pack, spec, value):
            return pack.to_stored(spec, value, warnings=[])

    import render_preset_panel as RP
    names = {amp: [n for n in RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY),
                                            pack, Dummy()) if n != "template"] for amp in config.amps}
    if config.split == "held_out":
        for slug in sorted(parts):
            for kind in ("measure", "net"):
                _require_complete(config, kind, slug, names)
    # Starting an onset attempt archived the primary too. Use that exact snapshot
    # as its input, and restore primary outputs only after the sensitivity succeeds.
    primary_config = replace(config, out=attempt["history"]) if config.lag_mode == "onset" else config
    frozen_A = _waveform_selections(primary_config, parts, names) if config.lag_mode == "onset" else {}
    jobs = [(config, s, _score_lag(parts[s], config), names, frozen_A.get(s)) for s in sorted(parts)
            if config.split == "held_out" or (config.out / "measure" / s / "done").exists()]
    with ProcessPoolExecutor(config.workers) as ex:
        D = dict(ex.map(_score_part, jobs))
    if config.split == "held_out" and set(D) != set(parts):
        raise ValueError("confirmation scoring did not return every selected part")
    _assert_manifest_unchanged(config)
    filename = "distances-onset.json" if config.lag_mode == "onset" else "distances.json"
    _atomic_json(config.out / filename, D)
    if config.split == "held_out":
        from learn import set3_confirmation

        # Preserve None refusals and let the separate module own confirmation gates.
        summary = set3_confirmation.summarize(D, parts, manifest)
        filename = "confirmation-onset.json" if config.lag_mode == "onset" else "confirmation.json"
        _atomic_json(config.out / filename, summary)
        if config.lag_mode == "onset":
            for name in ("distances.json", "confirmation.json"):
                _atomic_bytes(config.out / name, (attempt["history"] / name).read_bytes())
        waveform_path = config.out / "confirmation.json"
        onset_path = config.out / "confirmation-onset.json"
        verdict_path = config.out / "confirmation-verdict.json"
        if waveform_path.is_file() and onset_path.is_file():
            _assert_manifest_unchanged(config)
            verdict = set3_confirmation.combined_verdict(
                json.loads(waveform_path.read_text()), json.loads(onset_path.read_text()), config.amps)
            _atomic_json(verdict_path, verdict)
        elif verdict_path.exists():
            verdict_path.unlink()
        return D
    import kill_tests as K

    summary_all = {}
    for bs in BAND_SETS:
        for amp in list(config.amps) + ["best-of-3"]:
            rows = []
            for slug, res in D.items():
                p = parts[slug]
                # weights: each band's parts count 1/n (validation-set3.md); band_stat takes band medians
                row = {"part": slug, "band": p["band"], "gain": p["gain_class"]}

                def pick(key, amps):
                    best = None
                    for a in amps:
                        dd = {n: v for n, v in res.get(f"{bs}|{a}|{key}", {}).items() if v}
                        for n, v in dd.items():
                            if best is None or v < best[2]:
                                best = (a, n, v)
                    return best

                amps = config.amps if amp == "best-of-3" else (amp,)
                # template+R of the amp (for best-of-3: PR12's template, the product's default)
                tamp = ("pr12" if "pr12" in config.amps else config.amps[0]) if amp == "best-of-3" else amp
                tB = res[f"{bs}|{tamp}|measure_B"].get("template+R")
                if not tB:
                    continue
                lt = math.log(tB)

                def scored(b):
                    if b is None:
                        return None
                    v = res[f"{bs}|{b[0]}|measure_B"].get(b[1])
                    return math.log(v) - lt if v else None

                row["oracle"] = scored(pick("measure_A", amps))
                allB = [math.log(v) - lt for a in amps for v in res[f"{bs}|{a}|measure_B"].values() if v]
                row["best_B"] = min(allB) if allB else None
                for kind in REBUILT:
                    row[kind] = scored(pick(f"{kind}_A", amps))
                rows.append(row)
            summ = {k: K.band_stat(rows, k) for k in ["oracle", "best_B"] + list(REBUILT)}
            for a, b in (("net", "flatref"), ("netstem", "flatstem")):
                pr = [dict(band=r["band"], x=r[a] - r[b]) for r in rows
                      if r.get(a) is not None and r.get(b) is not None]
                summ[f"{a}_minus_{b}"] = K.band_stat(pr, "x")
            summary_all[f"{bs}|{amp}"] = {"summary": summ, "rows": rows}
            print(bs, amp, json.dumps({k: (v["band_median_log_ratio"], v["parts_better"], v["parts"],
                                           v["sign_flip_p_two_sided"]) if v else None
                                       for k, v in summ.items()}), flush=True)
    (config.out / "result.json").write_text(json.dumps(summary_all, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("render", "score"))
    ap.add_argument("--kinds", nargs="*", default=["measure", "flatref"])
    ap.add_argument("--model", default=str(MODEL))
    ap.add_argument("--split", choices=("development", "held_out"), default="development")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--amps", nargs="+", choices=AMPS, default=AMPS)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--lag-mode", choices=("waveform", "onset"), default="waveform")
    ap.add_argument("--confirmation-manifest", type=pathlib.Path)
    ap.add_argument("--shard", default="0/1", help="i/n: render every n-th part from the i-th")
    args = ap.parse_args(argv)
    config = RunConfig(split=args.split, out=args.out, amps=tuple(args.amps), workers=args.workers,
                       lag_mode=args.lag_mode, model=pathlib.Path(args.model),
                       confirmation_manifest=args.confirmation_manifest)
    if args.cmd == "render":
        i, n = (int(v) for v in args.shard.split("/"))
        render(args.kinds, args.model, (i, n), config=config)
    else:
        score(config=config)


if __name__ == "__main__":
    main()
