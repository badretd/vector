"""Persistent user settings."""
import json
import os
from pathlib import Path

DEFAULTS = {
    "language": "en",
    "mic_device_index": None,
    "mic_device_name": None,
    "remember_mic": True,
    "vosk_model_dir": "model",
    "ollama_model": None,
    "setup_complete": False,
    "send_mode": "enter",
}


def _config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    p = Path(base) / "vector_voice"
    p.mkdir(parents=True, exist_ok=True)
    return p


SETTINGS_PATH = _config_dir() / "settings.json"


class Settings:
    def __init__(self):
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception as e:
                print(f"[settings] load failed: {e}")

    def save(self):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[settings] save failed: {e}")

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.data[key] = value