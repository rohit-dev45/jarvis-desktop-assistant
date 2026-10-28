"""Settings loaded from environment variables / a .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional dependency
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    api_key: str = field(default_factory=lambda: os.environ.get("NVIDIA_API_KEY", "").strip())
    model: str = field(default_factory=lambda: os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"))
    base_url: str = field(default_factory=lambda: os.environ.get("NIM_BASE_URL", NIM_BASE_URL))
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("JARVIS_DATA_DIR", Path.home() / ".jarvis")))
    hotkey: str = field(default_factory=lambda: os.environ.get("JARVIS_HOTKEY", "ctrl+alt+j"))
    wake_word: str = field(default_factory=lambda: os.environ.get("JARVIS_WAKE_WORD", "hey_jarvis"))
    whisper_model: str = field(default_factory=lambda: os.environ.get("JARVIS_WHISPER_MODEL", "base.en"))
    use_edge_tts: bool = field(default_factory=lambda: _bool("JARVIS_EDGE_TTS", False))
    web_search: bool = field(default_factory=lambda: _bool("JARVIS_WEB_SEARCH", True))

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def search_roots(self) -> list[Path]:
        home = Path.home()
        return [p for p in (home / "Desktop", home / "Documents", home / "Downloads") if p.exists()] or [home]
