#!/usr/bin/env python3
"""Search the shortlist runs' transcripts for anything outside what the brief allows.

    python research/audit_shortlist_runs.py --sandbox-dir ~/shortlist-sandboxes \\
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
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from _cli import die, guarded

FACTORY = "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite"
def _main_checkout() -> pathlib.Path:
    import subprocess

    common = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "--git-common-dir"],
                            capture_output=True, text=True, check=True).stdout.strip()
    return (PLUGIN_ROOT / common).resolve().parent


# The interpreter the brief names: the main checkout's own environment.
PYTHON = str(_main_checkout() / ".venv" / "bin" / "python")
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
EMBEDDED = re.compile(r"(?:^|[\s'\"=(,:<>|&;])((?:/|~|\.\./)[^\s'\"),;:]*)")


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text", c.get("content", ""))) if isinstance(c, dict)
                         else str(c) for c in content)
    return json.dumps(content)


FACTORY_PREFIX = "/library/audio/presets/neural"   # a quoted factory path cut at a space
INTROSPECTION = re.compile(r"Path\.home|expanduser|environ|getenv|chr\(|os\.walk|scandir|"
                           r"listdir|glob\.glob|iterdir")
# Claude Code's own notes in a result, which name the session's folders: the cwd reset
# after a command that left the project, and where an oversized output was saved.
HARNESS_NOTES = re.compile(r"^Shell cwd was reset to .*$|Full output saved to: \S+", re.M)
SEGMENTS = re.compile(r"&&|\|\||;|\||\n")
SCRIPT_PATH = re.compile(r"""['"](~[^'"]*|/(?:Users|Library|Volumes|private|tmp|var|etc|opt|"""
                         r"""System|Applications|home)(?:/[^'"]*)?)['"]""")
CODE = re.compile(r"[()'\";,{}<>]")             # a word that is code or text, not a path


def inside(path: str, base: str, sandbox: str, *, read_factory: bool = True) -> bool:
    """Whether `path`, taken relative to `base`, resolves to an allowed place: the
    sandbox; the factory folder for reading, never `User/` in any case; the interpreter;
    the system's folders."""
    p = os.path.normpath(os.path.join(base, os.path.expanduser(path)))
    if p == sandbox or p.startswith(sandbox + "/"):
        return True
    low = p.lower()
    if read_factory and (low == FACTORY.lower() or low.startswith(FACTORY.lower() + "/")
                         or low.startswith(FACTORY_PREFIX)):
        return "/user/" not in (low + "/")[len(FACTORY):]
    return p == PYTHON or p.startswith(SYSTEM) or p in {s.rstrip("/") for s in SYSTEM}


def bash_flags(command: str, sandbox: str, cwd: str):
    """Flags for one Bash command. Without the opening `cd` it runs in `cwd` (the
    repository), and its relative paths are resolved there."""
    flags = []
    opening = re.match(rf"\s*cd\s+(['\"]?){re.escape(sandbox)}/?\1\s*(&&|;|\n|$)", command)
    base = sandbox if opening else cwd
    if not opening:
        flags.append("bash does not open with cd into the sandbox")
    rest = command[opening.end():] if opening else command
    if re.search(r"(^|[\s;&|(])cd(\s|$)", rest):
        flags.append("bash changes directory again")
    if "`" in rest or ("$" in rest and not harmless_dollars(rest)):
        flags.append("bash uses shell expansion")
    elif "$" in rest:
        flags.append("bash uses a harmless $ (a regex anchor or a loop's own variable)")
    if NETWORK.search(rest):
        flags.append("bash reaches for the network or a search tool")
    if INTROSPECTION.search(rest):
        flags.append("bash code looks around the file system")
    if BAD_IN_COMMANDS.search(command):
        flags.append("bash names the data root, ~/.claude or github")
    try:
        words = shlex.split(rest, posix=True)
    except ValueError:
        words = rest.split()
        flags.append("bash command does not parse")
    candidates, saw_path = [], False
    for w in words:
        value = w.split("=", 1)[1] if w.startswith("-") and "=" in w else w
        if CODE.search(value):
            # Code: check every path inside it. A lone "/" there is a string, not a path.
            candidates += [c for c in EMBEDDED.findall(value) if c != "/"]
        elif value.startswith(("/", "~", ".")) or "/" in value:
            candidates.append(value)               # a path, spaces and all
        saw_path = saw_path or bool(candidates)
    if not opening and not saw_path:
        flags.append("bash runs in the repository")
    for c in candidates:
        if not inside(c, base, sandbox):
            flags.append(f"bash path outside the sandbox: {c[:80]}")
    return flags


def harmless_dollars(text: str) -> bool:
    """Whether every `$` in `text` is a regex anchor (followed by a quote, `|`, `)` or
    the end) or the variable of a `for` loop the same command sets."""
    loops = set(re.findall(r"\bfor\s+(\w+)\s+in\b", text))
    for m in re.finditer(r"\$", text):
        after = text[m.end():]
        before = text[m.start() - 1:m.start()] if m.start() else ""
        if after[:1] in ("", "|", ")"):
            continue
        # A quote right after `$` ends a pattern only when the `$` itself ends a word;
        # at a word's start, `$'...'` is bash's ANSI-C quoting, which can spell any path.
        if after[:1] in ('"', "'") and before and not before.isspace() and before not in "=(":
            continue
        name = re.match(r"\{?(\w+)\}?", after)
        if name and name.group(1) in loops:
            continue
        return False
    return True


def script_flags(code: str, sandbox: str):
    """Flags for a script a run writes: the same look-around, network and path checks a
    Bash command gets, with paths taken relative to the sandbox."""
    flags = []
    if NETWORK.search(code):
        flags.append("script reaches for the network or a search tool")
    if INTROSPECTION.search(code):
        flags.append("script code looks around the file system")
    if BAD_IN_COMMANDS.search(code):
        flags.append("script names the data root, ~/.claude or github")
    # In code, a path is a string literal from a real root or `~`; a literal like
    # "/data" is a suffix joined onto a variable, and `//` is division.
    for c in SCRIPT_PATH.findall(code):
        if not inside(c, sandbox, sandbox):
            flags.append(f"script path outside the sandbox: {c[:80]}")
    return flags


def writes_and_factory(command: str):
    """(the G files a Bash command writes, whether it opens the factory folder), by
    segment: an `apply_spec` segment writes its `--out` unless it is a dry run."""
    written, factory = set(), False
    for segment in SEGMENTS.split(command):
        if "apply_spec" in segment and "--dry-run" not in segment:
            written |= set(re.findall(r"--out[=\s]+['\"]?\S*?(part-\d+)/(G[1-4])\.xml", segment))
        if FACTORY.lower() in segment.lower() or FACTORY_PREFIX in segment.lower():
            factory = True
    return written, factory


def audit(path: pathlib.Path, sandbox: str):
    """[(kind, tool, text)] for one transcript."""
    sandbox = os.path.normpath(sandbox)
    flags, searches, fetches = [], 0, 0
    calls, cwd = [], str(PLUGIN_ROOT)
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        cwd = entry.get("cwd") or cwd
        for block in (entry.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") in ("tool_use", "tool_result"):
                calls.append((block, cwd))
    g_written, before, after, factory_seen = set(), set(), set(), False
    for block, cwd in calls:
        if block["type"] == "tool_result":
            # Claude Code's own note after a command that left the project names it.
            text = HARNESS_NOTES.sub("", _text(block.get("content")))
            for bad in BAD_IN_RESULTS:
                if re.search(bad, text):
                    flags.append((f"result names {bad}", "result", ""))
            continue
        name, args = block.get("name"), block.get("input") or {}
        shown = json.dumps(args)[:200]
        if name in FORBIDDEN_TOOLS:
            flags.append(("forbidden tool", name, shown))
        elif name == "Bash":
            command = args.get("command", "")
            flags += [(k, name, command[:200]) for k in bash_flags(command, sandbox, cwd)]
            written, factory = writes_and_factory(command)
            g_written |= written
            (after if factory_seen else before).update(written)
            factory_seen = factory_seen or factory
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
            writes = name in ("Write", "Edit", "NotebookEdit")
            paths = [str(args[k]) for k in PATH_KEYS if args.get(k)]
            pattern = str(args.get("pattern") or "") if name == "Glob" else ""
            if name == "Glob" and not paths and pattern.startswith("/"):
                fixed = re.split(r"[*?\[{]", pattern, maxsplit=1)[0]
                paths = [fixed.rstrip("/") or "/"]
            if not paths:
                flags.append(("no explicit path", name, shown))
            for p in paths:
                if not os.path.isabs(p) or not inside(p, sandbox, sandbox, read_factory=not writes):
                    flags.append(("path outside the sandbox", name, p[:200]))
            climbing = pattern if name == "Glob" else str(args.get("glob") or "")
            if ".." in climbing or (climbing.startswith(("/", "~")) and
                                    not inside(climbing.split("*")[0] or "/", sandbox, sandbox)):
                flags.append(("pattern climbs out", name, shown))
            if name in ("Read", "Glob", "Grep") and any(
                    p.lower().startswith(FACTORY.lower()) for p in paths):
                factory_seen = True
            if writes and paths:
                for found in re.findall(r"(part-\d+)/(G[1-4])\.xml", paths[0]):
                    g_written.add(found)
                    (after if factory_seen else before).add(found)
                # A script the run writes and then runs is checked as its commands are.
                code = str(args.get("content") or args.get("new_string") or "")
                if paths[0].endswith((".py", ".sh")) and code:
                    flags += [(k, name, paths[0][:200]) for k in script_flags(code, sandbox)]
                    if FACTORY.lower() in code.lower():
                        factory_seen = True
    if searches > SEARCHES or fetches > FETCHES:
        flags.append(("over the web limit", "web", f"{searches} searches, {fetches} fetches"))
    if factory_seen and (not before or after):
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
