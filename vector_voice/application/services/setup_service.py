"""First-run setup orchestration, driven by a SetupView abstraction."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vector_voice.application.constants import DEFAULT_OLLAMA_MODEL
from vector_voice.domain.models import AppSettings
from vector_voice.domain.ports import (
    AudioDevicePort,
    LlmProviderPort,
    SettingsServicePort,
    TranslationServicePort,
    VoskModelInstallerPort,
)


class SetupView(Protocol):
    """UI surface required by the setup flow."""

    def choose_language(self, default: str) -> str | None: ...
    def show_message(self, title: str, message: str) -> None: ...
    def show_error(self, title: str, message: str) -> None: ...
    def confirm(self, title: str, message: str) -> bool: ...
    def choose_item(
        self, title: str, prompt: str, items: list[str], default_index: int
    ) -> str | None: ...
    def ask_remember_mic(self, title: str, message: str, yes: str, no: str) -> bool: ...


class SetupService:
    """Runs the setup steps in the original order: language → Vosk → Ollama → mic."""

    def __init__(
        self,
        settings: SettingsServicePort,
        translator: TranslationServicePort,
        view: SetupView,
        vosk_installer: VoskModelInstallerPort,
        audio: AudioDevicePort,
        ollama: LlmProviderPort,
        project_root: Path,
    ) -> None:
        self._settings = settings
        self._i18n = translator
        self._view = view
        self._vosk = vosk_installer
        self._audio = audio
        self._ollama = ollama
        self._root = project_root

    # -- public API -------------------------------------------------------

    def run(self) -> tuple[bool, int | None]:
        """Return (ok, device_index). ok=False means the user cancelled."""
        lang = self._view.choose_language(self._settings.get("language") or "en")
        if lang is None:
            return False, None
        self._settings.set("language", lang)
        self._i18n.set_language(lang)

        if not self._ensure_vosk_model():
            return False, None

        if not self._ensure_ollama():
            return False, None

        device = self._choose_microphone()
        if device is None:
            return False, None

        self._settings.set("setup_complete", True)
        self._settings.save()
        return True, device

    def resolve_microphone(self) -> int | None:
        """Return a valid device index for the saved mic, or None to re-ask."""
        if not self._settings.get("remember_mic", True):
            return None

        saved_index = self._settings.get("mic_device_index")
        saved_name = self._settings.get("mic_device_name")
        if saved_index is None and not saved_name:
            return None

        try:
            devices = self._audio.list_input_devices()
        except Exception:
            return None

        if isinstance(saved_index, int):
            for d in devices:
                if d.index == saved_index and (not saved_name or d.name == saved_name):
                    return saved_index

        if saved_name:
            for d in devices:
                if d.name == saved_name:
                    self._settings.set("mic_device_index", d.index)
                    return d.index

        return None

    def choose_microphone_dialog(self) -> int | None:
        """Startup re-prompt: device only, remember_mic flag preserved."""
        devices = self._audio.list_input_devices()
        if not devices:
            self._view.show_error(
                self._i18n.t("error"), self._i18n.t("mic_none")
            )
            return None

        default_index = self._audio.default_input_index()
        default_pos = 0
        for i, d in enumerate(devices):
            if d.index == default_index:
                default_pos = i
                break

        labels = [f"[{d.index}] {d.name}" for d in devices]
        choice = self._view.choose_item(
            self._i18n.t("mic_select_title"),
            self._i18n.t("mic_select_prompt"),
            labels,
            default_pos,
        )
        if choice is None:
            return None

        index = devices[labels.index(choice)].index
        self._store_mic(index)
        if self._settings.get("remember_mic", True):
            self._settings.save()
        return index

    # -- setup steps ------------------------------------------------------

    def _ensure_vosk_model(self) -> bool:
        model_dir = self._root / (self._settings.get("vosk_model_dir") or "model")
        if self._vosk.is_installed(str(model_dir)):
            return True

        data_dir = self._root / "data"
        archives = (
            sorted(p.name for p in data_dir.glob("vosk-model-*.zip"))
            if data_dir.is_dir()
            else []
        )

        if not archives:
            self._view.show_error(
                self._i18n.t("vosk_model_missing_title"),
                self._i18n.t("vosk_zip_not_found") + f"\n{data_dir}",
            )
            return True

        if not self._view.confirm(
            self._i18n.t("vosk_model_missing_title"),
            self._i18n.t("vosk_model_missing_msg"),
        ):
            return True

        choice = self._view.choose_item(
            self._i18n.t("setup_title"),
            self._i18n.t("vosk_select_archive"),
            archives,
            0,
        )
        if choice is None:
            return False

        try:
            self._vosk.install(str(data_dir / choice), str(model_dir))
        except Exception as exc:
            self._view.show_error(
                self._i18n.t("error"),
                f"{self._i18n.t('vosk_model_failed')}\n{exc}",
            )
            return False

        self._view.show_message(self._i18n.t("setup_title"), self._i18n.t("vosk_model_installed"))
        return True

    def _ensure_ollama(self) -> bool:
        while True:
            if not self._ollama.is_available():
                if not self._view.confirm(
                    self._i18n.t("ollama_not_found_title"),
                    self._i18n.t("ollama_not_found_msg"),
                ):
                    self._settings.set("ollama_model", DEFAULT_OLLAMA_MODEL)
                    return True
                continue

            models = self._ollama.list_models()
            if not models:
                self._view.show_message(
                    self._i18n.t("ollama_model_title"),
                    self._i18n.t("ollama_no_models"),
                )
                self._settings.set("ollama_model", DEFAULT_OLLAMA_MODEL)
                return True

            current = self._settings.get("ollama_model") or models[0]
            default_pos = models.index(current) if current in models else 0
            choice = self._view.choose_item(
                self._i18n.t("ollama_model_title"),
                self._i18n.t("ollama_model_prompt"),
                models,
                default_pos,
            )
            if choice is None:
                return False
            self._settings.set("ollama_model", choice)
            return True

    def _choose_microphone(self) -> int | None:
        devices = self._audio.list_input_devices()
        if not devices:
            self._view.show_error(self._i18n.t("error"), self._i18n.t("mic_none"))
            return None

        default_index = self._audio.default_input_index()
        default_pos = 0
        for i, d in enumerate(devices):
            if d.index == default_index:
                default_pos = i
                break

        labels = [f"[{d.index}] {d.name}" for d in devices]
        choice = self._view.choose_item(
            self._i18n.t("mic_select_title"),
            self._i18n.t("mic_select_prompt"),
            labels,
            default_pos,
        )
        if choice is None:
            return None

        index = devices[labels.index(choice)].index
        self._store_mic(index)
        remember = self._view.ask_remember_mic(
            self._i18n.t("mic_select_title"),
            self._i18n.t("mic_remember"),
            self._i18n.t("mic_remember_yes"),
            self._i18n.t("mic_remember_no"),
        )
        self._settings.set("remember_mic", remember)
        return index

    def _store_mic(self, index: int) -> None:
        try:
            info = self._audio.get_device(index)
            name: str | None = info.name
        except Exception:
            name = None
        self._settings.set("mic_device_index", index)
        self._settings.set("mic_device_name", name)