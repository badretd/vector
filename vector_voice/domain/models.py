"""Immutable domain models shared across the application."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Emotion(str, Enum):
    """Emotions the avatar can express. Values match LLM tags."""

    THINKING = "Thinking"
    SAD = "Sad"
    NEUTRAL = "Neutral"
    LAUGH = "Laugh"
    HAPPY = "Happy"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(e.value for e in cls)


class SendMode(str, Enum):
    """How the user's typed/spoken text gets sent to the LLM."""

    ENTER = "enter"
    TIMER = "timer"


class Language(str, Enum):
    EN = "en"
    RU = "ru"

    @classmethod
    def from_code(cls, code: str | None) -> "Language":
        try:
            return cls(code or "en")
        except ValueError:
            return cls.EN


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: str


@dataclass(frozen=True)
class MicrophoneInfo:
    index: int
    name: str
    default_samplerate: float
    is_default: bool = False
    max_input_channels: int = 1


@dataclass
class AppSettings:
    """User settings. Includes placeholders for planned features so that
    migrating them later does not require changing the storage layer."""

    language: str = Language.EN.value
    mic_device_index: int | None = None
    mic_device_name: str | None = None
    remember_mic: bool = True
    vosk_model_dir: str = "model"
    ollama_model: str | None = None
    setup_complete: bool = False
    send_mode: str = SendMode.ENTER.value

    llm_provider: str = "ollama"
    proxy_url: str | None = None
    theme_id: str = "default_dark"

    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    openrouter_url: str | None = None

    # -- serialization ---------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})