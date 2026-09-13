"""Typed access to persisted settings with change notification."""
from __future__ import annotations

from typing import Any

from vector_voice.domain.events import SettingsChanged
from vector_voice.domain.models import AppSettings
from vector_voice.domain.ports import (
    EventBusPort,
    SettingsRepositoryPort,
    SettingsServicePort,
)


class SettingsService(SettingsServicePort):
    def __init__(
        self,
        repository: SettingsRepositoryPort,
        event_bus: EventBusPort | None = None,
    ) -> None:
        self._repo = repository
        self._bus = event_bus
        self._data: AppSettings = repository.load()

    def all(self) -> AppSettings:
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._data, key, default)

    def set(self, key: str, value: Any) -> None:
        if not hasattr(self._data, key):
            raise AttributeError(f"Unknown settings key: {key}")
        setattr(self._data, key, value)
        if self._bus is not None:
            self._bus.publish(SettingsChanged(key=key, value=value))

    def save(self) -> None:
        self._repo.save(self._data)