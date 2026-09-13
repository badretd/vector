"""Simple synchronous event bus."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from vector_voice.domain.ports import EventBusPort


class SimpleEventBus(EventBusPort):
    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: object) -> None:
        for handler in self._subscribers.get(type(event), ()):
            try:
                handler(event)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[event_bus] handler failed: {exc}")