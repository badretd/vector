"""Composition root: builds every concrete adapter and wires the app."""
from __future__ import annotations

import sys
from pathlib import Path

from vosk import SetLogLevel

from vector_voice.application.constants import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_OPENROUTER_URL,
)
from vector_voice.application.services.conversation_service import ConversationService
from vector_voice.application.services.memory_service import MemoryService
from vector_voice.application.services.settings_service import SettingsService
from vector_voice.application.services.setup_service import SetupService
from vector_voice.application.services.speech_service import SpeechService
from vector_voice.domain.models import Language
from vector_voice.infrastructure.asset_repository import QtAssetRepository
from vector_voice.infrastructure.audio_adapter import SounddeviceAudioAdapter
from vector_voice.infrastructure.event_bus import SimpleEventBus
from vector_voice.infrastructure.http_client import RequestsHttpClientFactory
from vector_voice.infrastructure.llm.ollama import OllamaProvider
from vector_voice.infrastructure.llm.openrouter import OpenRouterProvider
from vector_voice.infrastructure.llm.registry import LlmProviderRegistry
from vector_voice.infrastructure.logger import get_logger, setup_logger
from vector_voice.infrastructure.memory.sqlite_memory_repository import (
    SqliteMemoryRepository,
)
from vector_voice.infrastructure.settings_repository import JsonSettingsRepository
from vector_voice.infrastructure.speech_adapter import VoskSpeechAdapter
from vector_voice.infrastructure.translation_service import DictTranslationService
from vector_voice.infrastructure.vosk_installer import ZipVoskModelInstaller
from vector_voice.presentation.qt.app import create_application
from vector_voice.presentation.qt.controller import MainWindowController
from vector_voice.presentation.qt.main_window import VoiceWindow
from vector_voice.presentation.qt.settings_dialog import SettingsDialog
from vector_voice.presentation.qt.setup_wizard import QtSetupView
from vector_voice.presentation.qt.theme import QtThemeManager
from vector_voice.presentation.qt.viewmodel import MainViewModel


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_under_root(root: Path, configured: str | None, default: str) -> Path:
    name = Path(configured).name if configured else default
    if not name:
        name = default
    return (root / name).resolve()


def _select_provider(providers: LlmProviderRegistry, settings: SettingsService):
    provider_id = settings.get("llm_provider") or "ollama"
    provider = providers.get(provider_id)
    if provider is None or not provider.is_available():
        provider = providers.get("ollama") or providers.default()
        provider_id = provider.provider_id
    if provider_id == "openrouter":
        model = settings.get("openrouter_model") or DEFAULT_OPENROUTER_MODEL
    else:
        model = settings.get("ollama_model") or DEFAULT_OLLAMA_MODEL
    return provider, model


def main() -> None:
    SetLogLevel(-1)

    project_root = _project_root()
    setup_logger(project_root)
    log = get_logger("bootstrap")
    log.info("Starting Vector Voice from %s", project_root)

    assets_dir = project_root / "assets"
    emotions_dir = project_root / "emotions"

    app = create_application()

    event_bus = SimpleEventBus()
    settings_repo = JsonSettingsRepository()
    settings = SettingsService(settings_repo, event_bus)

    i18n = DictTranslationService(settings.get("language") or Language.EN.value)
    audio = SounddeviceAudioAdapter()
    vosk_installer = ZipVoskModelInstaller()
    http_factory = RequestsHttpClientFactory(settings.get("proxy_url"))

    providers = LlmProviderRegistry()
    ollama = OllamaProvider(http_factory, DEFAULT_OLLAMA_URL)
    providers.register(ollama)

    openrouter = OpenRouterProvider(
        http_factory,
        api_key=settings.get("openrouter_api_key"),
        url=settings.get("openrouter_url") or DEFAULT_OPENROUTER_URL,
    )
    providers.register(openrouter)

    setup = SetupService(
        settings=settings,
        translator=i18n,
        view=QtSetupView(),
        vosk_installer=vosk_installer,
        audio=audio,
        ollama=ollama,
        project_root=project_root,
    )

    if not settings.get("setup_complete"):
        ok, device_index = setup.run()
        if not ok or device_index is None:
            print(i18n.t("setup_cancelled"))
            return
    else:
        device_index = setup.resolve_microphone()
        if device_index is None:
            device_index = setup.choose_microphone_dialog()
            if device_index is None:
                return

    model_dir = _resolve_under_root(
        project_root,
        settings.get("vosk_model_dir"),
        "model",
    )
    if not vosk_installer.is_installed(str(model_dir)):
        log.error("Vosk model missing at %s — speech recognition disabled", model_dir)
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.warning(
            None,
            i18n.t("vosk_model_missing_title"),
            f"{i18n.t('vosk_model_missing_msg')}\n{model_dir}",
        )
        return

    actual_rate = audio.pick_samplerate(device_index)

    speech_adapter = VoskSpeechAdapter(str(model_dir), device_index, actual_rate)
    speech = SpeechService(speech_adapter)

    # -- long-term memory ------------------------------------------------
    # Lives in the OS data directory, so a factory reset (reset_app.py)
    # never wipes it. See SqliteMemoryRepository.memory_db_path().
    memory_repo = SqliteMemoryRepository(settings.get("memory_db_path"))
    memory = MemoryService(memory_repo, settings)
    log.info("Memory store ready at %s", memory_repo._db_path)

    provider, model_name = _select_provider(providers, settings)
    conversation = ConversationService(provider, model_name, memory=memory)

    theme = QtThemeManager()
    assets = QtAssetRepository(assets_dir, emotions_dir)
    view_model = MainViewModel()
    view_model.send_mode = settings.get("send_mode", "enter")

    controller = MainWindowController(
        view_model=view_model,
        speech=speech,
        conversation=conversation,
        settings=settings,
        translator=i18n,
    )

    def open_settings(parent_widget):
        dialog = SettingsDialog(
            settings=settings,
            translator=i18n,
            audio=audio,
            providers=providers,
            http_factory=http_factory,
            conversation=conversation,
            theme=theme,
            project_root=project_root,
            memory=memory,
            parent=parent_widget,
        )
        dialog.exec_()

    window = VoiceWindow(
        view_model=view_model,
        controller=controller,
        assets=assets,
        translator=i18n,
        theme=theme,
        open_settings=open_settings,
    )

    speech.start()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()