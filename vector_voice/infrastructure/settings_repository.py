"""JSON-backed settings storage."""
from __future__ import annotations

import json
import os
from pathlib import Path

from vector_voice.domain.models import AppSettings
from vector_voice.domain.ports import SettingsRepositoryPort


def _config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "vector_voice"


def settings_path() -> Path:
    """Public helper used by reset_app.py."""
    return _config_dir() / "settings.json"


class JsonSettingsRepository(SettingsRepositoryPort):
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or settings_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppSettings.from_dict(data)
        except Exception as exc:
            print(f"[settings] load failed: {exc}")
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as exc:
            print(f"[settings] save failed: {exc}")