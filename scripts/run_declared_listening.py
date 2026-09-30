#!/usr/bin/env python3
"""Run a committed held-out listening protocol without showing its answers.

    python scripts/run_declared_listening.py --declaration docs/TEST.md \
        --runs runs/PRIVATE_NEW_DIRECTORY [--parallel 2]

The declaration needs one fenced JSON block with schema
``declared-listening-commands-v1`` and the same ``test_id`` as its
``held-out-listening-test-v1`` block. Its ``steps`` object has, in this order,
``crops``, ``di_match``, ``no_di_match``, ``di_preset``, ``no_di_preset``,
``first_render``, ``second_render``, ``manifest`` and ``audition``. Each step
contains ``argv`` (an argument array, never a shell command), ``outputs``
(files to hash), and ``primary_output`` (the file whose absence permits one
identical rerun). Match primary outputs must be named ``match-1.json``. Preset
steps additionally contain ``summary`` and ``fallback_argv``; a matching
"nothing beat the preset you started from" caveat selects the latter, which
must copy the declared template. Render steps contain
``applied_settings_record``, pointing to their fresh-render JSON sidecar.

Allowed placeholders are {python}, {repo}, {declaration}, {run}, {source},
{song}, {part}, {slug}, and {test_id}. All commands must invoke a tracked,
unchanged ``scripts/*.py`` through {python}. The block may change the arms'
commands, but cannot change the step names or skip a provenance check.

The new run directory must be under this worktree's ignored ``runs/`` tree,
which is also required by render_listening_guitar.py. Each part is private
and immutable. A failure stops that part; the record
retains both attempts and their logs. Successful steps conform to the v1
execution schema checked by summarize_declared_listening.py. The full pip
freeze text is kept privately at RUNS/pip-freeze.txt and bound by its hash.
Nothing from a step's stdout or stderr is printed to the listener.
The already-frozen heldout-sw50r declaration has no commands block, so this
runner intentionally refuses it; its archived run must not be replayed or
retroactively endowed with an execution record.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._cli import guarded
from scripts.build_validation_crops import _declaration
from scripts.score_listening import _require_private_out_dir


STEPS = ("crops", "di_match", "no_di_match", "di_preset", "no_di_preset",
         "first_render", "second_render", "manifest", "audition")
MATCHES = {"di_preset": "di_match", "no_di_preset": "no_di_match"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo: pathlib.Path, *args: str) -> str:
    done = subprocess.run(("git", "-C", str(repo), *args), capture_output=True,
                          text=True, check=False)
    if done.returncode:
        raise ValueError("a clean committed Git worktree is required")
    return done.stdout.strip()


def _check_clean(repo: pathlib.Path, head: str | None = None) -> str:
    current = _git(repo, "rev-parse", "HEAD")
    if head is not None and current != head:
        raise ValueError("worktree HEAD moved during the declared run")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("declared listening requires a clean worktree")
    return current


def _block(path: pathlib.Path) -> tuple[dict, dict]:
    def unique_keys(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate declaration key: {key}")
            result[key] = value
        return result

    content = path.read_text(encoding="utf-8")
    blocks = re.findall(r"^```json[ \t]*\r?\n(.*?)^```[ \t]*$", content,
                        flags=re.MULTILINE | re.DOTALL)
    parsed = []
    for block in blocks:
        if "held-out-listening-test-v1" in block or "declared-listening-commands-v1" in block:
            try:
                parsed.append(json.loads(block, object_pairs_hook=unique_keys))
            except json.JSONDecodeError as error:
                raise ValueError("invalid machine-readable declaration block") from error
    declaration = [item for item in parsed if isinstance(item, dict)
                   and item.get("schema") == "held-out-listening-test-v1"]
    commands = [item for item in parsed if isinstance(item, dict)
                and item.get("schema") == "declared-listening-commands-v1"]
    if len(declaration) != 1 or len(commands) != 1:
        raise ValueError("declaration needs one test block and one commands block")
    if commands[0].get("test_id") != declaration[0].get("test_id"):
        raise ValueError("command block names another declared test")
    if not isinstance(commands[0].get("template"), str):
        raise ValueError("command block must name its committed template")
    steps = commands[0].get("steps")
    if not isinstance(steps, dict) or set(steps) != set(STEPS):
        raise ValueError("command block must name every declared step exactly once")
    for name, spec in steps.items():
        if (not isinstance(spec, dict)
                or not isinstance(spec.get("argv"), list) or len(spec["argv"]) < 2
                or any(not isinstance(arg, str) for arg in spec["argv"])
                or not isinstance(spec.get("outputs"), list) or not spec["outputs"]
                or any(not isinstance(output, str) for output in spec["outputs"])
                or spec.get("primary_output") not in spec["outputs"]):
            raise ValueError(f"{name}: invalid command or declared outputs")
        if name in ("di_match", "no_di_match") and pathlib.Path(
                spec["primary_output"]).name != "match-1.json":
            raise ValueError(f"{name}: primary output must be match-1.json")
        if name in MATCHES and (not isinstance(spec.get("summary"), str)
                                or not isinstance(spec.get("fallback_argv"), list)
                                or len(spec["fallback_argv"]) < 2
                                or any(not isinstance(arg, str)
                                       for arg in spec["fallback_argv"])):
            raise ValueError(f"{name}: preset step needs a summary and fallback command")
        if name in MATCHES and spec["summary"] not in steps[MATCHES[name]]["outputs"]:
            raise ValueError(f"{name}: summary must be an output of its match step")
        if name in ("first_render", "second_render") and not isinstance(
                spec.get("applied_settings_record"), str):
            raise ValueError(f"{name}: missing fresh-render record path")
        if name in ("first_render", "second_render") and spec[
                "applied_settings_record"] not in spec["outputs"]:
            raise ValueError(f"{name}: fresh-render record must be a declared output")
    return declaration[0], commands[0]


def _slug(part_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", part_id.replace("/", "-"))


def _expanded(value: str, fields: dict[str, str]) -> str:
    try:
        return value.format_map(fields)
    except (KeyError, ValueError) as error:
        raise ValueError(f"unknown or malformed declaration placeholder: {value!r}") from error


def _output(value: str, fields: dict[str, str], part_dir: pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(_expanded(value, fields))
    if (path.name == "private-key.json"
            or not path.is_absolute() or not path.is_relative_to(part_dir)
            or not path.resolve().is_relative_to(part_dir)
            or path == part_dir or path.is_symlink()):
        raise ValueError("declared outputs must be non-key files inside their part directory")
    return path


def _argv(values: list[str], fields: dict[str, str], repo: pathlib.Path) -> list[str]:
    argv = [_expanded(value, fields) for value in values]
    if argv[0] != fields["python"]:
        raise ValueError("declared commands must use the chosen Python interpreter")
    script = pathlib.Path(argv[1])
    if script.is_absolute() or ".." in script.parts or script.parts[0] != "scripts" \
            or script.suffix != ".py":
        raise ValueError("declared commands must run a repository scripts/*.py file")
    target = repo / script
    if (target.is_symlink() or not target.is_file()
            or not target.resolve().is_relative_to(repo / "scripts")
            or not _git(repo, "ls-tree", "HEAD", "--", script.as_posix()).startswith(
                ("100644 blob ", "100755 blob "))):
        raise ValueError("declared script must be a tracked regular file at HEAD")
    return argv


def _hash_outputs(paths: list[pathlib.Path]) -> dict[str, str]:
    result = {}
    for path in paths:
        if path.is_symlink():
            raise ValueError("a declared output is a symlink")
        if path.is_file():
            result[str(path)] = _sha(path)
    return result


def _persist(path: pathlib.Path, record: dict) -> None:
    staged = path.with_suffix(".json.tmp")
    staged.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n",
                      encoding="utf-8")
    os.replace(staged, path)


def _fallback(summary_path: pathlib.Path) -> bool:
    if summary_path.is_symlink() or not summary_path.is_file():
        raise ValueError("preset step needs its match summary")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    caveats = summary.get("caveats") if isinstance(summary, dict) else None
    if not isinstance(caveats, list) or any(not isinstance(item, str) for item in caveats):
        raise ValueError("match summary lacks a valid caveat list")
    return any(item.startswith("nothing beat the preset you started from")
               for item in caveats)


def _run_step(name: str, spec: dict, part_dir: pathlib.Path,
              fields: dict[str, str], repo: pathlib.Path, head: str,
              print_lock: threading.Lock) -> dict:
    paths = [_output(value, fields, part_dir) for value in spec["outputs"]]
    primary = _output(spec["primary_output"], fields, part_dir)
    values = spec["argv"]
    variant = "declared"
    if name in MATCHES and _fallback(_output(spec["summary"], fields, part_dir)):
        values = spec["fallback_argv"]
        variant = "template-copy"
    argv = _argv(values, fields, repo)
    logs = part_dir / "logs"
    logs.mkdir(exist_ok=True)
    attempts = []
    for number in (1, 2):
        _check_clean(repo, head)
        started = _now()
        log = logs / f"{name}-{number}.log"
        with log.open("wb") as stream:
            try:
                done = subprocess.run(argv, cwd=repo, stdout=stream,
                                      stderr=subprocess.STDOUT, check=False)
                exit_code = done.returncode
            except OSError as error:
                stream.write(f"could not start declared command: {type(error).__name__}\n".encode())
                exit_code = 127
        ended = _now()
        outputs = _hash_outputs(paths)
        attempt = {"command": argv, "exit_code": exit_code,
                   "started_at": started, "ended_at": ended,
                   "log": {"path": str(log.relative_to(part_dir)), "sha256": _sha(log)},
                   "outputs": outputs}
        attempts.append(attempt)
        with print_lock:
            print(f"{part_dir.name}/{name} {exit_code}", flush=True)
        if exit_code == 0 and len(outputs) == len(paths):
            return {**attempt, "variant": variant, "attempts": attempts}
        # A partially published result is evidence of failure, not permission
        # to overwrite it. Matches alone use match-1.json as their output;
        # their intermediate trial store may be reused on the one rerun.
        wrote_output = (primary.is_file() if name in ("di_match", "no_di_match")
                        else bool(outputs))
        if wrote_output:
            break
    return {**attempts[-1], "variant": variant, "attempts": attempts,
            "failed": True}


def _identical(steps: dict, fields: dict[str, str], part_dir: pathlib.Path) -> bool:
    settings = []
    for name in ("first_render", "second_render"):
        path = _output(steps[name]["applied_settings_record"], fields, part_dir)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"{name} lacks its fresh-render record")
        record = json.loads(path.read_text(encoding="utf-8"))
        if (record.get("schema") != "listening-fresh-render-v1"
                or not isinstance(record.get("applied_settings"), dict)):
            raise ValueError(f"{name} lacks valid applied settings")
        settings.append(record["applied_settings"])
    return settings[0] == settings[1]


def _part(part_id: str, run_root: pathlib.Path, repo: pathlib.Path,
          declaration_path: pathlib.Path, binding: dict, commands: dict,
          interpreter: pathlib.Path, freeze_sha: str, template_sha: str,
          print_lock: threading.Lock) -> dict:
    part_dir = run_root / _slug(part_id)
    part_dir.mkdir()  # A published part must never be silently overwritten.
    source, song, part = part_id.split("/", 2)
    fields = {"python": str(interpreter), "repo": str(repo),
              "declaration": str(declaration_path), "run": str(part_dir),
              "source": source, "song": song, "part": part,
              "slug": part_dir.name, "test_id": binding["test_id"]}
    record = {"schema": "declared-listening-execution-v1",
              "declaration_sha256": binding["sha256"], "commit": binding["commit"],
              "head_commit": binding["head_commit"],
              "interpreter_pip_freeze_sha256": freeze_sha,
              "interpreter_pip_freeze": str(run_root / "pip-freeze.txt"),
              "part": part_id, "started_at": _now(), "status": "not_run", "steps": {}}
    path = part_dir / "execution.json"
    _persist(path, record)
    try:
        for name in STEPS:
            if name == "manifest" and _identical(commands["steps"], fields, part_dir):
                record["status"] = "run_identical_settings"
                break
            step = _run_step(name, commands["steps"][name], part_dir, fields,
                             repo, binding["head_commit"], print_lock)
            if name in MATCHES and step["variant"] == "template-copy" and not step.get("failed"):
                preset = _output(commands["steps"][name]["primary_output"], fields, part_dir)
                if _sha(preset) != template_sha:
                    step["failed"] = True
                    step["error"] = "fallback preset is not a byte copy of the template"
            record["steps"][name] = step
            _persist(path, record)
            if step.get("failed"):
                break
        else:
            record["status"] = "awaiting_verdict"
    except (ValueError, OSError) as error:
        record["error"] = f"{type(error).__name__}: {error}"
    record["ended_at"] = _now()
    _persist(path, record)
    return {"part": part_id, "status": record["status"]}


def run(declaration_path: pathlib.Path, run_root: pathlib.Path, *, parallel: int = 1,
        repo_root: pathlib.Path = ROOT, python: pathlib.Path = pathlib.Path(sys.executable)) -> list[dict]:
    """Execute only committed protocol data in a clean worktree."""
    if type(parallel) is not int or parallel < 1:
        raise ValueError("--parallel must be a positive integer")
    repo = repo_root.resolve()
    head = _check_clean(repo)
    declaration_path = ((repo / declaration_path).absolute()
                        if not declaration_path.is_absolute()
                        else declaration_path.absolute())
    if (declaration_path.is_symlink() or not declaration_path.is_file()
            or not declaration_path.is_relative_to(repo / "docs")
            or len(declaration_path.relative_to(repo).parts) != 2
            or declaration_path.suffix != ".md"):
        raise ValueError("runner needs a regular committed docs/*.md declaration")
    declaration, commands = _block(declaration_path)
    parts = declaration.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("declaration names no parts")
    binding = _declaration(declaration_path, parts[0], repo)
    if binding["head_commit"] != head or any(
            not isinstance(part, str) or len(part.split("/")) != 3 for part in parts):
        raise ValueError("declaration must name source/song/part in this HEAD")
    if len({_slug(part) for part in parts}) != len(parts):
        raise ValueError("declared part IDs collide on a run directory")
    template_name = pathlib.Path(commands["template"])
    template = repo / template_name
    if (template_name.is_absolute() or ".." in template_name.parts
            or template.is_symlink() or not template.is_file()
            or not template.resolve().is_relative_to(repo)
            or not _git(repo, "ls-tree", "HEAD", "--", template_name.as_posix()).startswith(
                ("100644 blob ", "100755 blob "))):
        raise ValueError("declared template must be a tracked regular file at HEAD")
    for part in parts[1:]:
        _declaration(declaration_path, part, repo)
    # A venv's python may be a symlink to the base interpreter. Resolving it
    # would discard the venv and record the wrong pip environment.
    interpreter = python.expanduser().absolute()
    if not interpreter.is_file():
        raise ValueError("chosen Python interpreter does not exist")
    if run_root.expanduser().is_symlink():
        raise ValueError("private run directory must not be a symlink")
    run_root = _require_private_out_dir(run_root)
    if (run_root.exists() or run_root.is_symlink()
            or not run_root.is_relative_to(repo / "runs")
            or run_root == repo / "runs"):
        raise ValueError("choose a new private run directory under this worktree's runs/")
    # Validate all command paths and output slots before starting any step.
    for part_id in parts:
        source, song, part = part_id.split("/", 2)
        part_dir = run_root / _slug(part_id)
        fields = {"python": str(interpreter), "repo": str(repo),
                  "declaration": str(declaration_path), "run": str(part_dir),
                  "source": source, "song": song, "part": part,
                  "slug": part_dir.name, "test_id": binding["test_id"]}
        for name, spec in commands["steps"].items():
            _argv(spec["argv"], fields, repo)
            if name in MATCHES:
                _argv(spec["fallback_argv"], fields, repo)
                _output(spec["summary"], fields, part_dir)
            if name in ("first_render", "second_render"):
                _output(spec["applied_settings_record"], fields, part_dir)
            for output in spec["outputs"]:
                _output(output, fields, part_dir)
            _output(spec["primary_output"], fields, part_dir)
    run_root.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir()
    freeze = subprocess.run((str(interpreter), "-m", "pip", "freeze"),
                            cwd=repo, capture_output=True, check=False)
    if freeze.returncode or not freeze.stdout:
        raise ValueError("could not capture the interpreter's full pip freeze")
    freeze_path = run_root / "pip-freeze.txt"
    freeze_path.write_bytes(freeze.stdout)
    _check_clean(repo, head)
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=min(parallel, len(parts))) as executor:
        jobs = {executor.submit(_part, part, run_root, repo, declaration_path,
                                binding, commands, interpreter, _sha(freeze_path),
                                _sha(template), lock): part
                for part in parts}
        completed = {jobs[job]: job.result() for job in as_completed(jobs)}
    _check_clean(repo, head)
    return [completed[part] for part in parts]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declaration", required=True, type=pathlib.Path)
    parser.add_argument("--runs", required=True, type=pathlib.Path)
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--python", type=pathlib.Path, default=pathlib.Path(sys.executable))
    args = parser.parse_args()
    run(args.declaration, args.runs, parallel=args.parallel, python=args.python)


if __name__ == "__main__":
    guarded(main)
