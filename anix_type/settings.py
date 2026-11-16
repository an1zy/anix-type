"""Settings & credentials for anix-type."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


def get_config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    config_dir = Path(base) / "anix-type"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@dataclass
class Settings:
    port: int = 8766
    language: str = "auto"  # "auto", "ru", "en"
    ai_enabled: bool = True
    ai_provider: str = "groq"  # "groq", "ollama", "openai", "none"
    groq_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "llama-3.1-8b-instant"

    @classmethod
    def load(cls) -> Settings:
        cfg_file = get_config_dir() / "settings.json"
        if not cfg_file.is_file():
            s = cls()
            s.save()
            return s
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()

    def save(self) -> None:
        cfg_file = get_config_dir() / "settings.json"
        try:
            cfg_file.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
