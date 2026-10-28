"""LLM loop: NVIDIA NIM (OpenAI-compatible) with tool calling."""
from __future__ import annotations

from typing import Any

from .router import ToolRouter
from .safety import is_blocked

SYSTEM_PROMPT = (
    "You are Jarvis, a concise voice assistant running on the user's Windows PC. "
    "Use the provided tools for any action on the computer. Never delete files, never ask for or handle passwords, "
    "and never invent tool results. Keep spoken replies to one or two short sentences."
)


class Brain:
    def __init__(self, router: ToolRouter, client: Any = None, model: str | None = None, max_steps: int = 5):
        self.router = router
        self.model = model or router.settings.model
        self.max_steps = max_steps
        if client is None:
            from openai import OpenAI

            key = router.settings.api_key
            if not key.startswith("nvapi-"):
                raise RuntimeError("Set NVIDIA_API_KEY (an nvapi- key from build.nvidia.com) in .env or your environment.")
            client = OpenAI(api_key=key, base_url=router.settings.base_url)
        self.client = client
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask(self, text: str) -> str:
        if is_blocked(text):
            return "I can't help with deleting things or handling credentials."
        self.history.append({"role": "user", "content": text})
        for _ in range(self.max_steps):
            resp = self.client.chat.completions.create(
                model=self.model, messages=self.history, tools=self.router.schemas(), tool_choice="auto", temperature=0.2, max_tokens=512
            )
            msg = resp.choices[0].message
            calls = getattr(msg, "tool_calls", None) or []
            if not calls:
                answer = (msg.content or "").strip()
                self.history.append({"role": "assistant", "content": answer})
                self._trim()
                return answer
            self.history.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls],
            })
            for c in calls:
                result = self.router.call(c.function.name, c.function.arguments)
                self.history.append({"role": "tool", "tool_call_id": c.id, "content": result})
        return "I stopped after too many steps."

    def _trim(self, keep: int = 20) -> None:
        if len(self.history) > keep + 1:
            rest = self.history[-keep:]
            while rest and rest[0]["role"] == "tool":
                rest.pop(0)
            self.history = [self.history[0]] + rest
