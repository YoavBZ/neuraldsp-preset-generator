#!/usr/bin/env python3
"""Search the shortlist runs' transcripts for anything outside what the brief allows.

    python scripts/audit_shortlist_runs.py --sandbox-dir ~/shortlist-sandboxes \\
        --transcript SONG=PATH [--transcript SONG=PATH ...] --json audit.json

`docs/song-only-shortlist-plan.md`, "Leak control". Each transcript is a subagent's
JSONL record. Every tool call is checked, and every tool result:

- Bash: the command must start with `cd <its sandbox>`, and may not name the data
  root, a checkout of this project (other than the interpreter the brief names),
  `~/.claude`, the home folder (`~/`, `$HOME`), a parent folder (`../`) or github.com;
- Read, Grep, Glob (and any other tool with a path): an absolute path inside the
  sandbox or the factory folder;
- WebFetch: not github.com;
- the Skill tool, or a nested agent: never;
- results: no text naming this project, its repository or the validation data.

It prints and writes every flag with the call's text, cut short; it never prints
results.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

FACTORY = "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite"
PYTHON = "/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python"
PATH_KEYS = ("file_path", "path", "notebook_path")
BAD_IN_COMMANDS = [r"ndsp-presets", r"neuraldsp-preset-generator(?!/\.venv/bin/python)",
                   r"/\.claude", r"(^|[\s'\"=])~/", r"\$HOME", r"\.\./", r"github\.com",
                   r"githubusercontent"]
BAD_IN_RESULTS = [r"YoavBZ", r"neuraldsp-preset-generator(?!/\.venv)", r"validation-crops",
                  r"amp-reach", r"reach-sets", r"runs/kill"]


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text", c.get("content", ""))) if isinstance(c, dict)
                         else str(c) for c in content)
    return json.dumps(content)


def audit(path: pathlib.Path, sandbox: str):
    """[(kind, tool, text)] for one transcript."""
    flags = []
    allowed = (sandbox.rstrip("/") + "/", FACTORY + "/")
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        for block in (entry.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name, args = block.get("name"), block.get("input") or {}
                if name in ("Skill", "Agent", "Task", "Workflow"):
                    flags.append(("forbidden tool", name, json.dumps(args)[:200]))
                elif name == "Bash":
                    command = args.get("command", "")
                    if not re.match(rf"\s*cd\s+['\"]?{re.escape(sandbox.rstrip('/'))}['\"]?\s*(&&|;|$)",
                                    command):
                        flags.append(("bash outside the sandbox", name, command[:200]))
                    for bad in BAD_IN_COMMANDS:
                        if re.search(bad, command):
                            flags.append((f"bash names {bad}", name, command[:200]))
                elif name == "WebFetch":
                    if re.search(r"github\.com|githubusercontent", args.get("url", "")):
                        flags.append(("github fetch", name, args.get("url", "")[:200]))
                elif name not in ("WebSearch", "StructuredOutput", "SubagentHandback",
                                  "TodoWrite", "ToolSearch"):
                    paths = [args[k] for k in PATH_KEYS if args.get(k)]
                    if not paths:
                        flags.append(("no explicit path", name, json.dumps(args)[:200]))
                    for p in paths:
                        if not str(p).startswith(allowed) and str(p) not in (sandbox, FACTORY):
                            flags.append(("path outside the sandbox", name, str(p)[:200]))
            elif block.get("type") == "tool_result":
                text = _text(block.get("content"))
                for bad in BAD_IN_RESULTS:
                    if re.search(bad, text):
                        flags.append((f"result names {bad}", "result", ""))
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
        sandbox = args.sandbox_dir.expanduser() / song
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
