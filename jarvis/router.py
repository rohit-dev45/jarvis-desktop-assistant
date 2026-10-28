"""Tool registry + router. The only path from the LLM to the computer."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from . import safety, tools
from .config import Settings
from .reminders import Reminders


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[..., str]
    needs_confirmation: bool = False

    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


_S = {"type": "string"}


class ToolRouter:
    def __init__(self, settings: Settings, confirm: safety.Confirmer = safety.console_confirm, notify: Callable[[str], None] = print):
        self.settings = settings
        self.confirm = confirm
        self.log = safety.ActionLog(settings.data_dir / "actions.log")
        self.reminders = Reminders(notify)
        notes = settings.data_dir / "notes.md"
        t = [
            Tool("open_app", "Open an allow-listed desktop app by name.", _obj({"name": _S}, ["name"]), tools.open_app),
            Tool("open_website", "Open a website URL or shortcut (youtube, github, linkedin, gmail).", _obj({"url_or_name": _S}, ["url_or_name"]), tools.open_website),
            Tool("search_files", "Find files by name in Desktop, Documents and Downloads.", _obj({"pattern": _S}, ["pattern"]),
                 lambda pattern: tools.search_files(pattern, settings.search_roots)),
            Tool("system_info", "Time, OS, CPU, RAM and battery.", _obj({}), tools.system_info),
            Tool("get_time", "Current local time and date.", _obj({}), tools.get_time),
            Tool("media_control", "Media/volume keys.", _obj({"action": {"type": "string", "enum": list(tools._MEDIA_KEYS)}, "steps": {"type": "integer"}}, ["action"]), tools.media_control),
            Tool("take_note", "Save a note.", _obj({"text": _S}, ["text"]), lambda text: tools.take_note(text, notes)),
            Tool("read_notes", "Read the latest notes.", _obj({}), lambda: tools.read_notes(notes)),
            Tool("set_reminder", "Remind the user after N minutes (while Jarvis runs).", _obj({"text": _S, "minutes": {"type": "number"}}, ["text", "minutes"]), self.reminders.add),
            Tool("run_shell", "Run a read-only diagnostic command (dir, ipconfig, systeminfo, tasklist, ping...). Requires user confirmation.",
                 _obj({"command": _S}, ["command"]), self._shell, needs_confirmation=True),
        ]
        if settings.web_search:
            t.append(Tool("web_search", "Open a web search in the browser.", _obj({"query": _S}, ["query"]), tools.web_search))
        self.tools = {x.name: x for x in t}

    def _shell(self, command: str) -> str:
        if not safety.shell_allowed(command):
            return "Blocked: only single read-only commands like dir, ipconfig, systeminfo, tasklist or ping are allowed."
        return tools.run_shell(command)

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self.tools.values()]

    def call(self, name: str, args: dict | str | None) -> str:
        if isinstance(args, str):
            try:
                args = json.loads(args or "{}")
            except json.JSONDecodeError:
                args = {}
        args = args or {}
        tool = self.tools.get(name)
        if tool is None:
            self.log.write(name, args, "rejected:not_allowlisted")
            return f"Tool '{name}' is not allowed."
        rule = safety.is_blocked(json.dumps(args))
        if rule:
            self.log.write(name, args, "blocked", rule)
            return "I won't do that: it looks destructive or involves credentials."
        if tool.needs_confirmation and not self.confirm(f"Jarvis wants to run {name} {args}. Allow?"):
            self.log.write(name, args, "declined")
            return "Cancelled. The user did not confirm."
        try:
            result = tool.func(**args)
            self.log.write(name, args, "ok", result)
            return result
        except TypeError as exc:
            self.log.write(name, args, "error", str(exc))
            return f"Bad arguments for {name}: {exc}"
        except Exception as exc:  # keep the assistant alive
            self.log.write(name, args, "error", str(exc))
            return f"{name} failed: {exc}"
