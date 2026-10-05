#!/usr/bin/env python3
"""Search the shortlist runs' transcripts for anything outside what the brief allows.

    python scripts/audit_shortlist_runs.py --sandbox-dir ~/shortlist-sandboxes \\
        --transcript SONG=PATH [--transcript SONG=PATH ...] --json audit.json

`docs/song-only-shortlist-plan.md`, "Leak control". Each transcript is a subagent's
JSONL record. It works from what the brief allows, and flags the rest:

- **Bash:** the command must open with `cd <its sandbox>`. After that it may hold no
  other `cd`, no shell expansion (`$`, backticks), no URL, no download or search
  tool, and no path (a word, a `--flag=value`, or a path inside quoted code) that
  resolves outside the sandbox, the factory folder, the interpreter the brief names
  or the system's own folders;
- **files (Read, Write, Edit, Grep, Glob):** an absolute path that resolves inside the
  sandbox, or the factory folder for reading (never `User/`). Glob and Grep patterns
  may not climb out;
- **web:** WebSearch must block github.com and githubusercontent.com, WebFetch may not
  open them, and the counts are held to the brief's limits;
- **order:** nothing opens the factory folder before every G1-G4 is written;
- **never:** the Skill tool, or a nested agent;
- **results:** no text naming this project, its repository or the validation data.

Each flag carries its kind and the call's text, cut short. It never prints a result.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shlex
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

FACTORY = "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite"
PYTHON = "/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python"
SYSTEM = ("/usr/", "/bin/", "/sbin/", "/opt/homebrew/bin/", "/dev/null", "/dev/stdout",
          "/dev/stderr")
SEARCHES, FETCHES = 8, 12
PATH_KEYS = ("file_path", "path", "notebook_path")
FORBIDDEN_TOOLS = {"Skill", "Agent", "Task", "Workflow"}
NETWORK = re.compile(r"\b(curl|wget|yt-dlp|youtube-dl|aria2c|mdfind|locate|osascript|"
                     r"git|gh|scp|rsync|ssh|pip3?|brew|sudo|nc)\b|urllib|requests|http\.client|"
                     r"socket|https?://")
BAD_IN_COMMANDS = re.compile(r"ndsp-presets|/\.claude|github")
BAD_IN_RESULTS = [r"YoavBZ", r"neuraldsp-preset-generator(?!/\.venv)", r"validation-crops",
                  r"amp-reach", r"reach-sets", r"runs/kill", r"ndsp-presets/references",
                  r"ndsp-presets/runs", r"references/datasets"]
EMBEDDED = re.compile(r"(?:^|[\s'\"=(,:])((?:/|~|\.\./)[^\s'\"),;:]*)")


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text", c.get("content", ""))) if isinstance(c, dict)
                         else str(c) for c in content)
    return json.dumps(content)


def inside(path: str, sandbox: str, *, read_factory: bool = True) -> bool:
    """Whether `path`, taken relative to the sandbox, resolves to an allowed place."""
    p = os.path.normpath(os.path.join(sandbox, os.path.expanduser(path)))
    if p == sandbox or p.startswith(sandbox + "/"):
        return True
    if read_factory and (p == FACTORY or p.startswith(FACTORY + "/")):
        return not (p + "/").startswith(FACTORY + "/User/")
    return p == PYTHON or p.startswith(SYSTEM) or p in {s.rstrip("/") for s in SYSTEM}


def bash_flags(command: str, sandbox: str):
    flags = []
    opening = re.match(rf"\s*cd\s+(['\"]?){re.escape(sandbox)}/?\1\s*(&&|;|\n|$)", command)
    if not opening:
        flags.append("bash does not open with cd into the sandbox")
    rest = command[opening.end():] if opening else command
    if re.search(r"(^|[\s;&|(])cd(\s|$)", rest):
        flags.append("bash changes directory again")
    if "`" in rest or "$" in rest:
        flags.append("bash uses shell expansion")
    if NETWORK.search(rest):
        flags.append("bash reaches for the network or a search tool")
    if BAD_IN_COMMANDS.search(command):
        flags.append("bash names the data root, ~/.claude or github")
    try:
        words = shlex.split(rest, posix=True)
    except ValueError:
        words = rest.split()
        flags.append("bash command does not parse")
    candidates = []
    for w in words:
        if w.startswith(("/", "~", ".")) or "/" in w:
            candidates.append(w.split("=", 1)[1] if w.startswith("-") and "=" in w else w)
        candidates += EMBEDDED.findall(w)
    for c in candidates:
        if not inside(c, sandbox):
            flags.append(f"bash path outside the sandbox: {c[:80]}")
    return flags


def audit(path: pathlib.Path, sandbox: str):
    """[(kind, tool, text)] for one transcript."""
    sandbox = os.path.normpath(sandbox)
    flags, searches, fetches = [], 0, 0
    calls = []
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        for block in (entry.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") in ("tool_use", "tool_result"):
                calls.append(block)
    g_written, factory_seen = set(), None
    for i, block in enumerate(calls):
        if block["type"] == "tool_result":
            text = _text(block.get("content"))
            for bad in BAD_IN_RESULTS:
                if re.search(bad, text):
                    flags.append((f"result names {bad}", "result", ""))
            continue
        name, args = block.get("name"), block.get("input") or {}
        shown = json.dumps(args)[:200]
        if name not in ("WebSearch", "WebFetch") and FACTORY in json.dumps(args):
            factory_seen = i if factory_seen is None else factory_seen
        if name in FORBIDDEN_TOOLS:
            flags.append(("forbidden tool", name, shown))
        elif name == "Bash":
            command = args.get("command", "")
            flags += [(k, name, command[:200]) for k in bash_flags(command, sandbox)]
            if "apply_spec" in command and "--dry-run" not in command:
                g_written |= set(re.findall(r"\b(part-\d+)/(G[1-4])\.xml", command))
        elif name == "WebSearch":
            searches += 1
            blocked = set(args.get("blocked_domains") or [])
            if not {"github.com", "githubusercontent.com"} <= blocked:
                flags.append(("search without the github block", name, shown))
        elif name == "WebFetch":
            fetches += 1
            if re.search(r"github\.com|githubusercontent", args.get("url", "")):
                flags.append(("github fetch", name, shown))
        elif name not in ("StructuredOutput", "SubagentHandback", "TodoWrite", "ToolSearch"):
            paths = [str(args[k]) for k in PATH_KEYS if args.get(k)]
            if not paths:
                flags.append(("no explicit path", name, shown))
            writes = name in ("Write", "Edit", "NotebookEdit")
            for p in paths:
                if not os.path.isabs(p) or not inside(p, sandbox, read_factory=not writes):
                    flags.append(("path outside the sandbox", name, p[:200]))
            for key in ("pattern", "glob"):
                pattern = str(args.get(key) or "")
                if name in ("Glob", "Grep") and (pattern.startswith(("/", "~")) or ".." in pattern):
                    flags.append(("pattern climbs out", name, shown))
            if writes:
                g_written |= set(re.findall(r"\b(part-\d+)/(G[1-4])\.xml", paths[0] if paths else ""))
    if searches > SEARCHES or fetches > FETCHES:
        flags.append(("over the web limit", "web", f"{searches} searches, {fetches} fetches"))
    if factory_seen is not None:
        # Every G written before the factory folder is first touched.
        before = set()
        for block in calls[:factory_seen]:
            if block["type"] == "tool_use" and block.get("name") == "Bash":
                command = (block.get("input") or {}).get("command", "")
                if "apply_spec" in command and "--dry-run" not in command:
                    before |= set(re.findall(r"\b(part-\d+)/(G[1-4])\.xml", command))
        if not g_written <= before or not before:
            flags.append(("factory opened before every G was written", "order", ""))
    return flags


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sandbox-dir", type=pathlib.Path, required=True)
    ap.add_argument("--transcript", action="append", required=True, metavar="SONG=PATH")
    ap.add_argument("--json", type=pathlib.Path)
    args = ap.parse_args()
    out = {}
    for item in args.transcript:
        song, _, path = item.partition("=")
        sandbox = args.sandbox_dir.expanduser().resolve() / song
        if not sandbox.is_dir():
            die(f"no sandbox {sandbox}")
        flags = audit(pathlib.Path(path).expanduser(), str(sandbox))
        out[song] = [{"kind": k, "tool": t, "text": x} for k, t, x in flags]
        print(f"{song}: {len(flags)} flag(s)")
        for k, t, x in flags:
            print(f"  {k} [{t}] {x}")
    if args.json:
        args.json.expanduser().write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    guarded(main)
