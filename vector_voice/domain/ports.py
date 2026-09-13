"""Abstract ports (interfaces) implemented by infrastructure adapters.

Application and presentation layers depend on these abstractions only.

Note: ports implemented by QObject subclasses (speech recognizer, LLM
provider) are declared as ``Protocol`` because QObject uses its own
metaclass and cannot be combined with ``ABCMeta``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Protocol, runtime_checkable

from vector_voice.domain.models import AppSettings, Message, MicrophoneInfo


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

class EventBusPort(ABC):
    @abstractmethod
    def publish(self, event: object) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None: ...


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class SettingsRepositoryPort(ABC):
    @abstractmethod
    def load(self) -> AppSettings: ...

    @abstractmethod
    def save(self, settings: AppSettings) -> None: ...


class SettingsServicePort(ABC):
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def save(self) -> None: ...

    @abstractmethod
    def all(self) -> AppSettings: ...


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

class TranslationServicePort(ABC):
    @abstractmethod
    def set_language(self, code: str) -> None: ...

    @abstractmethod
    def get_language(self) -> str: ...

    @abstractmethod
    def t(self, key: str, **kwargs: Any) -> str: ...


# ---------------------------------------------------------------------------
# Audio / speech
# ---------------------------------------------------------------------------

class AudioDevicePort(ABC):
    @abstractmethod
    def list_input_devices(self) -> list[MicrophoneInfo]: ...

    @abstractmethod
    def default_input_index(self) -> int | None: ...

    @abstractmethod
    def get_device(self, index: int) -> MicrophoneInfo: ...

    @abstractmethod
    def check_samplerate(self, index: int, rate: int) -> bool: ...

    @abstractmethod
    def pick_samplerate(self, index: int) -> int: ...


@runtime_checkable
class SpeechRecognizerPort(Protocol):
    """Callback-based speech recognizer. Implementations own their threading."""

    def set_text_callback(self, callback: Callable[[str], None]) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def reset(self) -> None: ...
    def set_enabled(self, enabled: bool) -> None: ...


class VoskModelInstallerPort(ABC):
    @abstractmethod
    def is_installed(self, path: str) -> bool: ...

    @abstractmethod
    def install(self, archive_path: str, target_dir: str) -> None: ...


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

@runtime_checkable
class LlmProviderPort(Protocol):
    """One LLM backend. Providers may be streaming."""

    provider_id: str

    def is_available(self) -> bool: ...
    def list_models(self) -> list[str]: ...

    def stream_chat(
        self,
        model: str,
        messages: list[Message],
        on_chunk: Callable[[str], None],
        on_done: Callable[[], None],
        on_error: Callable[[Exception], None],
    ) -> None: ...

    def cancel(self) -> None: ...


# ---------------------------------------------------------------------------
# Assets / avatar / theme
# ---------------------------------------------------------------------------

class AssetRepositoryPort(ABC):
    @abstractmethod
    def emotion_source_pixmap(self, emotion: str) -> Any: ...

    @abstractmethod
    def mic_off_source_pixmap(self) -> Any: ...

    @abstractmethod
    def settings_icon(self, size: int) -> Any: ...


@runtime_checkable
class AvatarRendererPort(Protocol):
    """Renderer contract for the avatar widget. Implementations supply QWidget."""

    def widget(self) -> Any: ...
    def set_emotion(self, emotion: str | None) -> None: ...
    def set_scale(self, scale: float) -> None: ...
    def refresh(self) -> None: ...


class ThemeManagerPort(ABC):
    @abstractmethod
    def apply(self, widget: Any) -> None: ...

    @abstractmethod
    def tokens(self) -> dict[str, Any]: ...