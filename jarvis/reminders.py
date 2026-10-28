"""In-process reminders (they live while Jarvis is running)."""
from __future__ import annotations

import threading
from typing import Callable


class Reminders:
    def __init__(self, notify: Callable[[str], None]):
        self.notify = notify
        self.timers: list[threading.Timer] = []

    def add(self, text: str, minutes: float) -> str:
        minutes = float(minutes)
        if not 0 < minutes <= 24 * 60:
            return "Reminders must be between 0 and 1440 minutes."
        t = threading.Timer(minutes * 60, self.notify, args=(f"Reminder: {text}",))
        t.daemon = True
        t.start()
        self.timers.append(t)
        return f"I'll remind you in {minutes:g} minutes."

    def cancel_all(self) -> None:
        for t in self.timers:
            t.cancel()
