"""Attach one human A/B decision to the render and to learned tone notes.

The SQLite row is the machine-readable ground truth.  The learned note is the
human-readable feedback channel the preset skills already use.  This module writes
both from the same validated summary candidate so neither can drift into an
unmeasured adjective detached from the audio it describes.

No analysis dependency: listening results must remain recordable on a bare clone.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import pathlib
import re
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from match.store import STORE_NAME, Run, Store, StoreError, Trial
from packs.paths import data_root, learned_tones_path

CHOICES = ("candidate", "template", "indistinguishable")
# How many bands of the fingerprint delta a learned note keeps, and how far below
# the target's own peak band one still counts as audible. See _worst_bands.
NOTE_BANDS = 5
NOTE_FLOOR_DB = 50.0
_PACK_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_TOLERANCE = 1e-9


class VerdictError(ValueError):
    """A summary, candidate, or verdict that cannot safely be recorded."""


@dataclass(frozen=True)
class RecordedVerdict:
    run_id: str
    trial_id: int
    candidate: int
    choice: str
    notes_path: pathlib.Path


@dataclass(frozen=True)
class ValidatedCandidate:
    """One summary/spec/store candidate proved to describe the same render."""

    directory: pathlib.Path
    summary: Mapping[str, Any]
    candidate: Mapping[str, Any]
    spec: Mapping[str, Any]
    parameters: Mapping[str, Any]
    run: Run
    trial: Trial


def validate_candidate(
    run_dir: str | pathlib.Path, candidate_rank: int,
) -> ValidatedCandidate:
    """Resolve and cross-check a candidate without recording a verdict."""
    directory = pathlib.Path(run_dir).expanduser().resolve()
    summary = _read_object(directory / "summary.json", "summary")
    run_id, _pack, candidate = _validate_summary(summary, candidate_rank)
    spec = _read_object(directory / f"match-{candidate_rank}.json", "candidate spec")
    parameters = _spec_parameters(spec)
    _validate_changes(candidate, parameters)
    store_path = directory / STORE_NAME
    if not store_path.is_file():
        raise VerdictError(f"the run has no render store at {store_path}")
    with Store(str(store_path)) as store:
        trial = _resolve_trial(store, run_id, summary, candidate, parameters)
        run = store.run(run_id)
    return ValidatedCandidate(
        directory, summary, candidate, spec, parameters, run, trial,
    )


def candidate_binding_sha256(validated: ValidatedCandidate) -> str:
    """Digest every durable object that identifies the auditioned render."""
    material = {
        "summary": validated.summary,
        "spec": validated.spec,
        "run": asdict(validated.run),
        "trial": asdict(validated.trial),
    }
    encoded = json.dumps(
        material, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def record_verdict(
    run_dir: str | pathlib.Path,
    *,
    candidate_rank: int,
    choice: str,
    listener: str,
    comment: Optional[str] = None,
) -> RecordedVerdict:
    """Record a template-versus-candidate audition from a completed match run."""
    directory = pathlib.Path(run_dir).expanduser().resolve()
    summary = _read_object(directory / "summary.json", "summary")
    run_id, pack, candidate = _validate_summary(summary, candidate_rank)
    spec = _read_object(directory / f"match-{candidate_rank}.json", "candidate spec")
    parameters = _spec_parameters(spec)
    _validate_changes(candidate, parameters)

    choice = str(choice).strip()
    if choice not in CHOICES:
        raise VerdictError(
            f"unknown listening choice {choice!r}; choose one of: "
            f"{', '.join(CHOICES)}"
        )
    listener = str(listener).strip()
    if not listener:
        raise VerdictError("--listener cannot be empty")
    if comment is not None:
        comment = str(comment).strip() or None

    store_path = directory / STORE_NAME
    if not store_path.is_file():
        raise VerdictError(f"the run has no render store at {store_path}")

    notes = _safe_notes_path(pack)
    notes.parent.mkdir(parents=True, exist_ok=True)
    if notes.is_symlink():
        raise VerdictError(
            f"refusing to replace the learned-notes symlink at {notes}; pass a "
            f"--data-dir containing a regular file instead"
        )

    with Store(str(store_path)) as store:
        trial = _resolve_trial(store, run_id, summary, candidate, parameters)
        if trial.trial_id is None:
            raise VerdictError("the resolved render has no trial id")
        with _notes_lock(notes):
            if notes.is_symlink():
                raise VerdictError(
                    f"refusing to replace the learned-notes symlink at {notes}"
                )
            _record_with_intent(
                store, directory, notes, summary, candidate, trial, candidate_rank,
                choice, listener, comment,
            )

    return RecordedVerdict(run_id, trial.trial_id, candidate_rank, choice, notes)


def _read_object(path: pathlib.Path, label: str) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise VerdictError(f"the run has no {label} at {path}") from e
    if not isinstance(value, dict):
        raise VerdictError(f"the {label} at {path} must be a JSON object")
    return value


def _validate_summary(summary: Mapping[str, Any], rank: int):
    if summary.get("schema") != "tone-match-summary-v1":
        raise VerdictError(
            f"unsupported summary schema {summary.get('schema')!r}; expected "
            f"'tone-match-summary-v1'"
        )
    run_id = summary.get("run_id")
    pack = summary.get("pack")
    if not isinstance(run_id, str) or not run_id.strip():
        raise VerdictError("the summary has no run_id")
    if not isinstance(pack, str) or not _PACK_ID.fullmatch(pack):
        raise VerdictError(f"the summary has an unsafe or missing pack id: {pack!r}")
    shortlist = summary.get("shortlist")
    if not isinstance(shortlist, list) or not shortlist:
        raise VerdictError("the summary has no shortlist to audition")
    if rank < 1 or rank > len(shortlist):
        raise VerdictError(
            f"candidate {rank} is not in this run; choose 1 through {len(shortlist)}"
        )
    candidate = shortlist[rank - 1]
    if not isinstance(candidate, dict) or candidate.get("rank") != rank:
        raise VerdictError(
            f"shortlist entry {rank} does not identify itself as candidate {rank}"
        )
    renderer = summary.get("renderer")
    if not isinstance(renderer, dict) or not isinstance(
            renderer.get("renderer_id"), str):
        raise VerdictError("the summary has no renderer identity")
    if not isinstance(renderer.get("reproducible"), bool):
        raise VerdictError("the summary does not say whether its renderer is reproducible")
    if (renderer["reproducible"] is False
            and not _is_number(renderer.get("band_noise_db"))):
        raise VerdictError(
            "a non-reproducible renderer summary needs its measured band_noise_db"
        )
    return run_id, pack, candidate


def _spec_parameters(spec: Mapping[str, Any]) -> Dict[str, Any]:
    items = spec.get("parameters")
    if not isinstance(items, list) or not items:
        raise VerdictError("the candidate spec has no parameters")
    result: Dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            raise VerdictError("every candidate spec parameter must be an object")
        module, key = item.get("module"), item.get("key")
        if not isinstance(module, str) or not isinstance(key, str) or not key:
            raise VerdictError("a candidate spec parameter has no module/key path")
        # Root parameters have appeared in stores as both ``selectedAmp`` and
        # ``/selectedAmp`` depending on whether the caller started from renderer
        # settings or tuple-keyed search values. They name the same preset field.
        path = _parameter_path(f"{module}/{key}")
        if path in result:
            raise VerdictError(f"candidate spec repeats parameter {path!r}")
        if "value" not in item:
            raise VerdictError(f"candidate spec parameter {path!r} has no value")
        result[path] = item["value"]
    return result


def _validate_changes(candidate: Mapping[str, Any], parameters: Mapping[str, Any]) -> None:
    changes = candidate.get("changes")
    if not isinstance(changes, list):
        raise VerdictError("the summary candidate has no parameter change list")
    seen = set()
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("path"), str):
            raise VerdictError("a summary parameter change has no path")
        path = _parameter_path(change["path"])
        if path in seen:
            raise VerdictError(f"the summary repeats parameter change {path!r}")
        seen.add(path)
        if path not in parameters or "to" not in change or not _same_value(
                change["to"], parameters[path]):
            raise VerdictError(
                f"summary change {change['path']!r} does not match the candidate spec"
            )


def _resolve_trial(store: Store, run_id: str, summary: Mapping[str, Any],
                   candidate: Mapping[str, Any], parameters: Mapping[str, Any]) -> Trial:
    summary_run = store.run(run_id)
    trial_id = candidate.get("trial_id")
    if trial_id is not None:
        if isinstance(trial_id, bool) or not isinstance(trial_id, int) or trial_id < 1:
            raise VerdictError(f"candidate trial_id is invalid: {trial_id!r}")
        trial = store.trial(trial_id)
        _validate_trial(trial, summary, candidate, parameters)
        source_run = store.run(trial.run_id or "")
        _validate_context(source_run, summary_run, summary)
        return trial

    # Summaries written before trial ids were added can still be used, but only when
    # score + complete rendered parameter subset identify exactly one reference-level
    # trial. Ambiguity is refused; guessing would attach human ground truth to the
    # wrong render, which is worse than not recording it.
    matches = [trial for trial in store.trials(run_id)
               if _trial_matches(trial, summary, candidate, parameters)]
    if not matches:
        for run in store.runs():
            if run.run_id == run_id:
                continue
            if _contexts_match(run, summary_run, summary):
                matches.extend(trial for trial in store.trials(run.run_id)
                               if _trial_matches(trial, summary, candidate, parameters))
    if len(matches) != 1:
        reason = "none" if not matches else str(len(matches))
        raise VerdictError(
            f"this legacy summary has no trial_id and its candidate matched {reason} "
            f"render-store rows; re-run the match with the current code rather than "
            f"attaching a verdict by guess"
        )
    return matches[0]


def _validate_trial(trial: Trial, summary: Mapping[str, Any], candidate: Mapping[str, Any],
                    parameters: Mapping[str, Any]) -> None:
    if not _trial_matches(trial, summary, candidate, parameters):
        raise VerdictError(
            f"candidate trial_id {trial.trial_id} does not match its score and spec; "
            f"the summary, spec, and render store are not from the same result"
        )


def _trial_matches(trial: Trial, summary: Mapping[str, Any], candidate: Mapping[str, Any],
                   parameters: Mapping[str, Any]) -> bool:
    if trial.failed or abs(float(trial.di_offset_db)) > _TOLERANCE:
        return False
    score = candidate.get("score")
    measured = (trial.objectives or {}).get("total")
    if not _same_number(score, measured):
        return False
    if not _same_structure(candidate.get("objectives"), trial.objectives):
        return False
    if not isinstance(trial.fingerprint, dict):
        return False
    target = ((summary.get("reference") or {}).get("fingerprint") or {})
    expected_delta = _band_delta(target, trial.fingerprint)
    reported_delta = candidate.get("fingerprint_delta")
    if not _valid_band_delta(reported_delta, target):
        return False
    # The report fingerprint is a separate render made after the search. A
    # reproducible backend must produce the stored trial's exact delta; a reused
    # Swift instance explicitly does not, and its summary carries the measured noise
    # floor that qualifies the second render instead.
    reproducible = (summary.get("renderer") or {}).get("reproducible")
    report_fingerprint = candidate.get("fingerprint")
    if report_fingerprint is not None:
        if (not isinstance(report_fingerprint, dict)
                or not _same_structure(
                    reported_delta, _band_delta(target, report_fingerprint))):
            return False
    elif reproducible is True and not _same_structure(reported_delta, expected_delta):
        return False
    for path, value in trial.params.items():
        canonical = _parameter_path(path)
        if canonical not in parameters or not _same_value(parameters[canonical], value):
            return False
    return bool(trial.params)


def _validate_context(source_run, summary_run, summary: Mapping[str, Any]) -> None:
    if not _contexts_match(source_run, summary_run, summary):
        raise VerdictError(
            f"candidate trial {source_run.run_id!r} was measured under a different "
            f"reference, pack, regime, loss profile, renderer, or plugin version "
            f"than summary run {summary_run.run_id!r}"
        )


def _contexts_match(source_run, summary_run, summary: Mapping[str, Any]) -> bool:
    reference = summary.get("reference") or {}
    fingerprint = reference.get("fingerprint") or {}
    source = fingerprint.get("source") or {}
    sha = source.get("sha256")
    renderer = summary.get("renderer") or {}
    basic = (
        isinstance(sha, str)
        and source_run.reference_sha == sha
        and summary_run.reference_sha == sha
        and source_run.pack == summary_run.pack == summary.get("pack")
        and source_run.loss_profile == summary_run.loss_profile
        == summary.get("loss_profile")
        and source_run.regime == summary_run.regime == reference.get("regime")
        and source_run.renderer_id == summary_run.renderer_id
        == renderer.get("renderer_id")
        and source_run.plugin_version == summary_run.plugin_version
        == renderer.get("plugin_version")
    )
    if not basic:
        return False
    # New runs persist the complete renderer metadata in the otherwise free-form
    # notes column. Legacy M6 rows contain only their probe caveat, so their durable
    # renderer identity/version are still checked above and the remaining metadata is
    # explicitly treated as legacy summary data.
    for run in (source_run, summary_run):
        stored = _stored_renderer(run)
        if stored is not None and not _same_structure(stored, renderer):
            return False
    return True


def _stored_renderer(run) -> Optional[Mapping[str, Any]]:
    if not run.notes:
        return None
    try:
        value = json.loads(run.notes)
    except (TypeError, json.JSONDecodeError):
        return None
    if (not isinstance(value, dict)
            or value.get("schema") != "tone-match-run-notes-v1"
            or not isinstance(value.get("renderer"), dict)):
        return None
    return value["renderer"]


def _is_number(value: Any) -> bool:
    """A finite JSON number, which ``True`` and ``None`` and ``NaN`` are not."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _same_number(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        a, b = float(left), float(right)
    except (TypeError, ValueError):
        return False
    return math.isfinite(a) and math.isfinite(b) and math.isclose(
        a, b, rel_tol=_TOLERANCE, abs_tol=_TOLERANCE
    )


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return _same_number(left, right)
    return type(left) is type(right) and left == right


def _same_structure(left: Any, right: Any) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _same_structure(left[key], right[key]) for key in left)
    if (isinstance(left, Sequence) and not isinstance(left, (str, bytes))
            and isinstance(right, Sequence) and not isinstance(right, (str, bytes))):
        return len(left) == len(right) and all(
            _same_structure(a, b) for a, b in zip(left, right))
    if (isinstance(left, (int, float)) and not isinstance(left, bool)
            and isinstance(right, (int, float)) and not isinstance(right, bool)):
        return _same_number(left, right)
    return type(left) is type(right) and left == right


def _parameter_path(path: str) -> str:
    return str(path).lstrip("/")


def _band_delta(target: Mapping[str, Any], candidate: Mapping[str, Any]):
    target_spectrum = target.get("spectrum") or {}
    candidate_spectrum = candidate.get("spectrum") or {}
    centres = target_spectrum.get("band_centres_hz") or []
    target_levels = target_spectrum.get("band_db") or []
    candidate_map = dict(zip(candidate_spectrum.get("band_centres_hz") or [],
                             candidate_spectrum.get("band_db") or []))
    target_map = dict(zip(centres, target_levels))
    shared = [centre for centre in centres if centre in candidate_map]
    if not shared:
        return []
    differences = {centre: target_map[centre] - candidate_map[centre]
                   for centre in shared}
    offset = sum(differences.values()) / len(differences)
    return [{
        "centre_hz": float(centre),
        "target_db": float(target_map[centre]),
        "candidate_db": float(candidate_map[centre]),
        "delta_db": float(differences[centre] - offset),
    } for centre in shared]


def _valid_band_delta(value: Any, target: Mapping[str, Any]) -> bool:
    if not isinstance(value, list):
        return False
    keys = {"centre_hz", "target_db", "candidate_db", "delta_db"}
    if not all(isinstance(item, dict) and set(item) == keys
               and all(_is_number(item[key]) for key in keys)
               for item in value):
        return False
    spectrum = target.get("spectrum") or {}
    target_map = dict(zip(spectrum.get("band_centres_hz") or [],
                          spectrum.get("band_db") or []))
    if any(item["centre_hz"] not in target_map
           or not _same_number(item["target_db"], target_map[item["centre_hz"]])
           for item in value):
        return False
    if not value:
        return True
    differences = [item["target_db"] - item["candidate_db"] for item in value]
    offset = sum(differences) / len(differences)
    return all(_same_number(item["delta_db"], difference - offset)
               for item, difference in zip(value, differences))


def _safe_notes_path(pack: str) -> pathlib.Path:
    root = data_root().resolve()
    destination = learned_tones_path(pack)
    resolved = destination.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise VerdictError(
            f"learned-notes path {resolved} escapes the data root {root}"
        )
    return destination


@contextmanager
def _notes_lock(notes: pathlib.Path):
    """Serialise every run that appends to this pack's one learned-notes file."""
    try:
        import fcntl
    except ImportError as e:  # pragma: no cover - this project currently ships on POSIX
        raise VerdictError(
            "recording a listening verdict needs an operating-system file lock, "
            "which this platform does not provide"
        ) from e
    lock_path = notes.parent / f".{notes.name}.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _record_with_intent(store: Store, run_dir: pathlib.Path, notes: pathlib.Path,
                        summary: Mapping[str, Any], candidate: Mapping[str, Any],
                        trial: Trial, rank: int, choice: str, listener: str,
                        comment: Optional[str]) -> None:
    """Commit database first, then idempotently reconcile the note after a crash."""
    if trial.trial_id is None:
        raise VerdictError("cannot record a verdict for a trial without an id")
    source_run = store.run(trial.run_id or "")
    identity = _intent_identity(store.path, trial.trial_id, listener)
    intent_path = run_dir / f".verdict-intent-{identity}.json"

    if intent_path.exists():
        intent = _read_object(intent_path, "pending verdict intent")
        created_at = intent.get("created_at")
        if not _is_number(created_at):
            raise VerdictError(f"pending verdict intent {intent_path} has no timestamp")
    else:
        previous = store.verdict(trial.trial_id, listener)
        if previous is not None:
            raise StoreError(
                f"listener {listener!r} already recorded {previous['choice']!r} "
                f"for trial {trial.trial_id}; use a distinct listener/session name "
                f"for another independent audition"
            )
        created_at = time.time()
        intent = {
            "schema": "tone-match-verdict-intent-v1",
            "identity": identity,
            "trial_id": trial.trial_id,
            "run_id": summary.get("run_id"),
            "candidate": rank,
            "listener": listener,
            "choice": choice,
            "comment": comment,
            "created_at": created_at,
            "notes_path": str(notes.resolve()),
        }

    entry = _note_entry(summary, candidate, trial, source_run, rank, choice, listener,
                        comment, float(created_at), identity)
    expected = {
        "schema": "tone-match-verdict-intent-v1",
        "identity": identity,
        "trial_id": trial.trial_id,
        "run_id": summary.get("run_id"),
        "candidate": rank,
        "listener": listener,
        "choice": choice,
        "comment": comment,
        "created_at": float(created_at),
        "notes_path": str(notes.resolve()),
    }
    if not _same_structure(intent, expected):
        raise VerdictError(
            f"pending verdict intent {intent_path} belongs to a different command; "
            f"repeat the original choice, listener, comment, and --data-dir to "
            f"finish its recovery"
        )
    if not intent_path.exists():
        _atomic_replace(intent_path, json.dumps(intent, indent=2) + "\n", 0o600)

    recorded = store.verdict(trial.trial_id, listener)
    if recorded is None:
        store.add_verdict(trial.trial_id, listener, choice, comment,
                          created_at=float(created_at))
    elif not _same_structure(
            {key: recorded[key] for key in ("trial_id", "listener", "choice",
                                             "comment", "created_at")},
            {"trial_id": trial.trial_id, "listener": listener, "choice": choice,
             "comment": comment, "created_at": float(created_at)}):
        raise VerdictError(
            f"database verdict for trial {trial.trial_id} disagrees with pending "
            f"intent {intent_path}; neither record was changed"
        )

    _append_note_once(notes, entry, identity)
    intent_path.unlink()
    _fsync_directory(run_dir)


def _intent_identity(store_path: str, trial_id: int, listener: str) -> str:
    payload = json.dumps([str(pathlib.Path(store_path).resolve()), trial_id, listener],
                         ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _append_note_once(notes: pathlib.Path, entry: str, identity: str) -> None:
    previous = notes.read_text(encoding="utf-8") if notes.exists() else ""
    marker = f"<!-- verdict:{identity} -->"
    if marker in previous:
        return
    mode = notes.stat().st_mode & 0o777 if notes.exists() else 0o600
    _atomic_replace(notes, _append_entry(previous, entry), mode)


def _note_entry(summary: Mapping[str, Any], candidate: Mapping[str, Any],
                trial: Trial, source_run, rank: int, choice: str, listener: str,
                comment: Optional[str], created_at: float, identity: str) -> str:
    reference = summary.get("reference") or {}
    renderer = summary.get("renderer") or {}
    starting = summary.get("starting_point") or {}
    stamp = datetime.fromtimestamp(created_at, timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    reproducible = renderer.get("reproducible")
    qualification = (
        "reproducible=false; the candidate objectives and fingerprint delta came "
        "from separate reused-instance renders; the backend reports an approximate "
        f"{_json(renderer.get('band_noise_db'))} dB per-band noise floor, not a bound"
        if reproducible is False else f"reproducible={_json(reproducible)}"
    )
    verdict = {
        "listener": listener,
        "choice": choice,
        "comparison": f"candidate-{rank}-vs-template",
        "comment": comment,
    }
    measurement = {
        "renderer": source_run.renderer_id,
        "plugin_version": source_run.plugin_version,
        "loss_profile": source_run.loss_profile,
        "starting_score": starting.get("reference_level_score",
                                       starting.get("score")),
        "candidate_score": candidate.get("reference_level_score",
                                         (trial.objectives or {}).get("total")),
        "starting_observations": starting.get("observations", 1),
        "candidate_observations": (
            (candidate.get("input_level_observations") or {}).get("0.0", 1)
        ),
        "starting_spread": starting.get("spread"),
        "candidate_spread": (
            (candidate.get("input_level_spread") or {}).get("0.0")
        ),
        "starting_trial_score": starting.get("score"),
        "candidate_trial_score": (trial.objectives or {}).get("total"),
        "objectives": trial.objectives,
    }
    bands, label = _worst_bands(candidate.get("fingerprint_delta"))
    return "\n".join([
        f"### {stamp} — run {_json(summary.get('run_id'))}, candidate {rank}",
        f"- Reference: SHA-256 {_json(source_run.reference_sha)}; regime "
        f"{_json(source_run.regime)}; confidence "
        f"{_json(reference.get('regime_confidence'))}",
        f"- Measurement ({qualification}): {_json(measurement)}",
        f"- Fingerprint delta{label}: {_json(bands)}",
        f"- Parameter changes: {_json(candidate.get('changes'))}",
        f"- Verdict on trial {trial.trial_id}: {_json(verdict)}",
        f"<!-- verdict:{identity} -->",
    ])


def _worst_bands(delta: Any):
    """The bands that carry the difference, and a label that admits the rest.

    The whole 30-band delta is 3,498 of a 5,649-byte entry — 62% of a file the
    generate and edit skills read in full before choosing values. Both copies of
    the array live in the run's summary.json either way, so nothing is lost by
    naming the subset rather than transcribing it into a file that only grows.

    Deviation alone is the wrong subset, and the M6 Hotel California run shows why:
    third-octave level falls away 50-80 dB at both ends of the spectrum, the fitted
    error there is correspondingly large, and ranking on |delta_db| spent two of
    candidate 1's five slots — and three of candidate 3's — on bands 54 to 81 dB
    below the target's loudest. Those are the noise floor. Candidate 3 lost 80 Hz
    entirely, which is the band the listener was describing.

    So the ranking runs over bands within NOTE_FLOOR_DB of the target's own peak
    band: 50 dB down is 0.3% of the amplitude of the loudest thing in the recording.
    On that run it leaves 24 of 30 bands eligible for all three candidates and keeps
    the low mids for each. The label states the window, because a subset chosen by
    an audibility judgement has to say that is what it is.

    Printed low frequency to high, because that is the order a tone gets described
    in. The peak band always survives its own window, so the eligible set is never
    empty for a delta that has entries at all.
    """
    if not isinstance(delta, list) or len(delta) <= NOTE_BANDS:
        return delta, ""
    peak = max(float(band["target_db"]) for band in delta)
    eligible = [band for band in delta
                if float(band["target_db"]) >= peak - NOTE_FLOOR_DB]
    worst = sorted(eligible, key=lambda band: -abs(float(band["delta_db"])))[:NOTE_BANDS]
    worst.sort(key=lambda band: float(band["centre_hz"]))
    return worst, (
        f" (the {len(worst)} largest deviations among the {len(eligible)} bands "
        f"within {NOTE_FLOOR_DB:g} dB of the target's peak; all {len(delta)} bands "
        f"are in this run's summary.json)")


def _json(value: Any) -> str:
    # Escaping HTML metacharacters keeps a comment copied from elsewhere from
    # becoming active markup when a Markdown viewer renders this local file.
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).replace("&", "\\u0026").replace(
                          "<", "\\u003c").replace(">", "\\u003e")


def _append_entry(previous: str, entry: str) -> str:
    if not previous.strip():
        return "# Learned tones\n\n" + entry + "\n"
    return previous.rstrip() + "\n\n" + entry + "\n"


def _temporary(directory: pathlib.Path, content: str, mode: int) -> pathlib.Path:
    descriptor, name = tempfile.mkstemp(prefix=".learned-tones-", dir=directory)
    path = pathlib.Path(name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        path.unlink(missing_ok=True)
        raise
    return path


def _atomic_replace(destination: pathlib.Path, content: str, mode: int) -> None:
    temporary = _temporary(destination.parent, content, mode)
    try:
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _fsync_directory(directory: pathlib.Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
