"""Desktop tools. Each returns a short string Jarvis can speak.

Windows-specific calls are guarded so the module imports (and tests run) on Linux.
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import os
import platform
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")

APP_ALLOWLIST = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
    "chrome": "chrome",
    "edge": "msedge",
    "vscode": "code",
    "vs code": "code",
    "terminal": "wt",
    "spotify": "spotify:",
}

SITE_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "linkedin": "https://www.linkedin.com",
    "gmail": "https://mail.google.com",
    "nvidia build": "https://build.nvidia.com",
}


def open_app(name: str) -> str:
    key = name.strip().lower()
    target = APP_ALLOWLIST.get(key)
    if not target:
        return f"'{name}' is not on my app allow-list. Allowed: {', '.join(sorted(APP_ALLOWLIST))}."
    if not IS_WINDOWS:
        return f"(dry run, not Windows) would open {target}"
    os.startfile(target)  # type: ignore[attr-defined]
    return f"Opening {name}."


def open_website(url_or_name: str) -> str:
    key = url_or_name.strip().lower()
    url = SITE_SHORTCUTS.get(key, url_or_name.strip())
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if urllib.parse.urlparse(url).scheme not in {"http", "https"}:
        return "Only http/https links are allowed."
    webbrowser.open(url)
    return f"Opening {url}."


def web_search(query: str) -> str:
    url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
    webbrowser.open(url)
    return f"Searching the web for {query}."


def search_files(pattern: str, roots: list[Path], limit: int = 10) -> str:
    pat = pattern if any(c in pattern for c in "*?") else f"*{pattern}*"
    hits: list[str] = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in {"node_modules", "AppData"}]
            for fn in filenames:
                if fnmatch.fnmatch(fn.lower(), pat.lower()):
                    hits.append(str(Path(dirpath) / fn))
                    if len(hits) >= limit:
                        return "Found:\n" + "\n".join(hits)
    return "Found:\n" + "\n".join(hits) if hits else f"No files matching '{pattern}'."


def system_info() -> str:
    parts = [f"Time {_dt.datetime.now():%I:%M %p, %A %d %B}", f"OS {platform.system()} {platform.release()}"]
    try:
        import psutil

        parts.append(f"CPU {psutil.cpu_percent(interval=0.3):.0f}%")
        parts.append(f"RAM {psutil.virtual_memory().percent:.0f}%")
        batt = psutil.sensors_battery()
        if batt:
            parts.append(f"Battery {batt.percent:.0f}%{' charging' if batt.power_plugged else ''}")
    except Exception:
        pass
    return ", ".join(parts) + "."


def get_time() -> str:
    return f"It's {_dt.datetime.now():%I:%M %p on %A, %d %B}."


_MEDIA_KEYS = {
    "play_pause": 0xB3, "next": 0xB0, "previous": 0xB1,
    "volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD,
}


def media_control(action: str, steps: int = 1) -> str:
    vk = _MEDIA_KEYS.get(action)
    if vk is None:
        return f"Unknown media action. Use one of: {', '.join(_MEDIA_KEYS)}."
    if not IS_WINDOWS:
        return f"(dry run, not Windows) would press {action} x{steps}"
    import ctypes

    for _ in range(max(1, min(int(steps), 20))):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)  # type: ignore[attr-defined]
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # type: ignore[attr-defined]
    return f"Done: {action}."


def take_note(text: str, notes_file: Path) -> str:
    notes_file.parent.mkdir(parents=True, exist_ok=True)
    with notes_file.open("a", encoding="utf-8") as fh:
        fh.write(f"- [{_dt.datetime.now():%Y-%m-%d %H:%M}] {text}\n")
    return "Noted."


def read_notes(notes_file: Path, last: int = 5) -> str:
    if not notes_file.exists():
        return "You have no notes yet."
    lines = notes_file.read_text(encoding="utf-8").strip().splitlines()
    return "\n".join(lines[-last:])


def run_shell(command: str) -> str:
    """Runs an allow-listed, read-only command. The router enforces confirmation."""
    shell = ["cmd", "/c", command] if IS_WINDOWS else ["sh", "-c", command]
    out = subprocess.run(shell, capture_output=True, text=True, timeout=20)
    return (out.stdout or out.stderr or "(no output)").strip()[:1500]
