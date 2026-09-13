"""Composition root: builds every concrete adapter and wires the app."""
from __future__ import annotations

import sys
from pathlib import Path

from vosk import SetLogLevel

from vector_voice.application.constants import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_URL
from vector_voice.application.services.conversation_service import ConversationService
from vector_voice.application.services.settings_service import SettingsService
from vector_voice.application.services.setup_service import SetupService
from vector_voice.application.services.speech_service import SpeechService
from vector_voice.domain.models import Language
from vector_voice.infrastructure.asset_repository import QtAssetRepository
from vector_voice.infrastructure.audio_adapter import SounddeviceAudioAdapter
from vector_voice.infrastructure.event_bus import SimpleEventBus
from vector_voice.infrastructure.http_client import RequestsHttpClientFactory
from vector_voice.infrastructure.llm.ollama import OllamaProvider
from vector_voice.infrastructure.llm.registry import LlmProviderRegistry
from vector_voice.infrastructure.settings_repository import JsonSettingsRepository
from vector_voice.infrastructure.speech_adapter import VoskSpeechAdapter
from vector_voice.infrastructure.translation_service import DictTranslationService
from vector_voice.infrastructure.vosk_installer import ZipVoskModelInstaller
from vector_voice.presentation.qt.app import create_application
from vector_voice.presentation.qt.controller import MainWindowController
from vector_voice.presentation.qt.main_window import VoiceWindow
from vector_voice.presentation.qt.setup_wizard import QtSetupView
from vector_voice.presentation.qt.theme import QtThemeManager
from vector_voice.presentation.qt.viewmodel import MainViewModel


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    SetLogLevel(-1)

    project_root = _project_root()
    assets_dir = project_root / "assets"
    emotions_dir = project_root / "emotions"

    app = create_application()

    # --- Infrastructure -------------------------------------------------
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

    # --- Setup / microphone resolution ---------------------------------
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

    # --- Runtime overrides ---------------------------------------------
    model_path = str(project_root / settings.get("vosk_model_dir", "model"))
    actual_rate = audio.pick_samplerate(device_index)

    # --- Application services ------------------------------------------
    speech_adapter = VoskSpeechAdapter(model_path, device_index, actual_rate)
    speech = SpeechService(speech_adapter)

    model_name = settings.get("ollama_model") or DEFAULT_OLLAMA_MODEL
    conversation = ConversationService(providers.default(), model_name)

    # --- Presentation ---------------------------------------------------
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

    window = VoiceWindow(
        view_model=view_model,
        controller=controller,
        assets=assets,
        translator=i18n,
        theme=theme,
    )

    # Start listening only after the window is fully wired so that no
    # recognition event can be lost in the gap between VM updates and
    # UI subscriptions.
    speech.start()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()