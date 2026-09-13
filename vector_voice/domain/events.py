"""Domain events published through the EventBus."""
from __future__ import annotations

from dataclasses import dataclass

from vector_voice.domain.models import Emotion


@dataclass(frozen=True)
class SpeechRecognized:
    text: str


@dataclass(frozen=True)
class LlmChunkReceived:
    text: str


@dataclass(frozen=True)
class LlmEmotionReceived:
    emotion: Emotion


@dataclass(frozen=True)
class LlmFinished:
    pass


@dataclass(frozen=True)
class MicToggled:
    enabled: bool


@dataclass(frozen=True)
class SettingsChanged:
    key: str
    value: object