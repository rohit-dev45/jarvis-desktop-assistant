"""Entry point: python -m jarvis [--text | --hotkey | --wake]"""
from __future__ import annotations

import argparse

from .brain import Brain
from .config import Settings
from .router import ToolRouter


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="jarvis", description="Safety-first desktop voice assistant (NVIDIA NIM).")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--text", action="store_true", help="type instead of speaking (default)")
    mode.add_argument("--hotkey", action="store_true", help="push-to-talk with a global hotkey")
    mode.add_argument("--wake", action="store_true", help="hands-free with the 'Hey Jarvis' wake word")
    p.add_argument("--seconds", type=float, default=5.0, help="recording length per command")
    args = p.parse_args(argv)

    settings = Settings()
    from .voice import Speaker

    speaker = Speaker(settings.use_edge_tts) if (args.hotkey or args.wake) else None
    out = speaker.say if speaker else (lambda s: print(f"Jarvis: {s}"))
    router = ToolRouter(settings, notify=out)
    try:
        brain = Brain(router)
    except RuntimeError as exc:
        raise SystemExit(str(exc))

    if not (args.hotkey or args.wake):
        print("Jarvis text mode. Type 'exit' to quit.")
        while True:
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text.lower() in {"exit", "quit"}:
                break
            if text:
                out(brain.ask(text))
        return

    from .voice import Listener, wait_for_hotkey, wait_for_wake_word

    listener = Listener(settings.whisper_model)
    out("Jarvis online.")
    while True:
        try:
            wait_for_wake_word(settings.wake_word) if args.wake else wait_for_hotkey(settings.hotkey)
            out("Yes?")
            text = listener.transcribe(listener.record(args.seconds))
            print(f"You: {text}")
            if not text:
                continue
            if text.lower().strip(" .!") in {"goodbye", "exit", "shut down jarvis"}:
                out("Goodbye.")
                break
            out(brain.ask(text))
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
