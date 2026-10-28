"""Safety policy: allow-list, confirmation gate, and an action log.

Rules
- Only tools registered in the router can run (allow-list).
- Tools marked ``needs_confirmation`` (shell commands, closing apps, etc.)
  run only after the user says/types "yes".
- No tool deletes files, and requests that look destructive or ask for
  credentials are refused before any tool runs.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Callable

BLOCKED_PATTERNS = [
    r"\b(rm|del|erase|rmdir|rd|format|diskpart|shred)\b",
    r"remove-item|\bdelete\b|\bwipe\b",
    r"\bshutdown\b|\brestart-computer\b|\bstop-computer\b",
    r"\breg(\.exe)?\s+(delete|add)\b",
    r"\bcipher\s+/w\b",
    r"invoke-webrequest|\biwr\b|\bcurl\b.*\|\s*(sh|iex)|\biex\b",
    r"password|passwd|api[_ -]?key|secret|token|credential",
]
_BLOCKED = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]

# Read-only shell commands that may run (still after confirmation).
SAFE_SHELL_PREFIXES = ("dir", "ipconfig", "systeminfo", "tasklist", "whoami", "hostname", "ping", "echo", "ver", "ls", "pwd", "uname", "date")


def is_blocked(text: str) -> str | None:
    """Return the matching rule if ``text`` looks destructive or credential-related."""
    for pat in _BLOCKED:
        if pat.search(text or ""):
            return pat.pattern
    return None


def shell_allowed(command: str) -> bool:
    cmd = command.strip().lower()
    if not cmd or is_blocked(cmd) or any(ch in cmd for ch in "&|;><`$"):
        return False
    return cmd.split()[0] in SAFE_SHELL_PREFIXES


class ActionLog:
    """Append-only JSON-lines log of every tool call and its outcome."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, tool: str, args: dict, status: str, result: str = "") -> None:
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "tool": tool, "args": args, "status": status, "result": result[:300]}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


Confirmer = Callable[[str], bool]


def console_confirm(prompt: str) -> bool:
    return input(f"{prompt} [yes/no]: ").strip().lower() in {"y", "yes"}
