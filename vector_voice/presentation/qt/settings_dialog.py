"""Full settings dialog with factory reset."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from vector_voice.application.services.memory_service import MemoryService

from vector_voice.application.constants import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENROUTER_MODEL,
)
from vector_voice.application.services.conversation_service import ConversationService
from vector_voice.application.services.settings_service import SettingsService
from vector_voice.domain.ports import AudioDevicePort, TranslationServicePort
from vector_voice.infrastructure.http_client import RequestsHttpClientFactory
from vector_voice.infrastructure.llm.registry import LlmProviderRegistry
from vector_voice.presentation.qt.theme import QtThemeManager


def _mask_key(key: str | None) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "\u2022" * len(key)
    return f"{key[:4]}\u2026{key[-4:]}"


class SettingsDialog(QDialog):
    """Edits all user-facing settings and can trigger a factory reset."""

    def __init__(
        self,
        settings: SettingsService,
        translator: TranslationServicePort,
        audio: AudioDevicePort,
        providers: LlmProviderRegistry,
        http_factory: RequestsHttpClientFactory,
        conversation: ConversationService,
        theme: QtThemeManager,
        project_root: Path,
        memory: MemoryService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._i18n = translator
        self._audio = audio
        self._providers = providers
        self._http = http_factory
        self._conversation = conversation
        self._theme = theme
        self._root = project_root
        self._memory = memory
        self._clear_key_flag = False

        self.setWindowTitle(translator.t("settings_title"))
        self.setMinimumWidth(620)
        self.setModal(True)
        self.setStyleSheet(theme.dialog_stylesheet())

        self._build_ui()
        self._load_current()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Русский", "ru")
        form.addRow(self._make_label(self._i18n.t("settings_language")), self.lang_combo)

        self.send_mode_combo = QComboBox()
        self.send_mode_combo.addItem(self._i18n.t("settings_send_enter"), "enter")
        self.send_mode_combo.addItem(self._i18n.t("settings_send_timer"), "timer")
        form.addRow(
            self._make_label(self._i18n.t("settings_send_mode_header")),
            self.send_mode_combo,
        )

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Ollama", "ollama")
        self.provider_combo.addItem("OpenRouter", "openrouter")
        form.addRow(
            self._make_label(self._i18n.t("settings_llm_provider")),
            self.provider_combo,
        )

        self.mic_combo = QComboBox()
        form.addRow(self._make_label(self._i18n.t("mic_select_title")), self.mic_combo)

        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setEditable(True)
        form.addRow(
            self._make_label(self._i18n.t("settings_ollama_model")),
            self.ollama_model_combo,
        )

        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.setSpacing(6)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText(self._i18n.t("settings_key_unset"))
        self.key_clear_btn = QPushButton(self._i18n.t("settings_clear_key"))
        self.key_clear_btn.clicked.connect(self._on_clear_key)
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(self.key_clear_btn)

        self.key_label = QLabel()
        self.key_label.setStyleSheet("color: #888888; font-size: 9pt;")

        key_box = QVBoxLayout()
        key_box.setContentsMargins(0, 0, 0, 0)
        key_box.setSpacing(2)
        key_box.addLayout(key_row)
        key_box.addWidget(self.key_label)
        form.addRow(
            self._make_label(self._i18n.t("settings_openrouter_key")),
            key_box,
        )

        self.openrouter_model_combo = QComboBox()
        self.openrouter_model_combo.setEditable(True)
        form.addRow(
            self._make_label(self._i18n.t("settings_openrouter_model")),
            self.openrouter_model_combo,
        )

        self.proxy_edit = QLineEdit()
        self.proxy_edit.setPlaceholderText(self._i18n.t("settings_proxy_placeholder"))
        form.addRow(self._make_label(self._i18n.t("settings_proxy")), self.proxy_edit)

        memory_box = QVBoxLayout()
        memory_box.setContentsMargins(0, 0, 0, 0)
        memory_box.setSpacing(4)

        self.memory_check = QCheckBox(self._i18n.t("settings_memory_enabled"))
        memory_box.addWidget(self.memory_check)

        memory_row = QHBoxLayout()
        memory_row.setContentsMargins(0, 0, 0, 0)
        memory_row.setSpacing(6)
        self.memory_info = QLabel()
        self.memory_info.setStyleSheet("color: #888888; font-size: 9pt;")
        memory_row.addWidget(self.memory_info, 1)
        self.memory_clear_btn = QPushButton(self._i18n.t("settings_memory_clear"))
        self.memory_clear_btn.clicked.connect(self._on_clear_memory)
        memory_row.addWidget(self.memory_clear_btn)
        memory_box.addLayout(memory_row)

        form.addRow(
            self._make_label(self._i18n.t("settings_memory_header")),
            memory_box,
        )

        root.addLayout(form)
        root.addStretch(1)

        btn_row = QHBoxLayout()
        self.reset_btn = QPushButton(self._i18n.t("settings_factory_reset"))
        self.reset_btn.clicked.connect(self._on_factory_reset)
        btn_row.addWidget(self.reset_btn)
        btn_row.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        root.addLayout(btn_row)

    @staticmethod
    def _make_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setMinimumWidth(160)
        return label

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------

    def _load_current(self) -> None:
        s = self._settings.all()

        idx = self.lang_combo.findData(s.language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)

        idx = self.send_mode_combo.findData(s.send_mode)
        if idx >= 0:
            self.send_mode_combo.setCurrentIndex(idx)

        idx = self.provider_combo.findData(s.llm_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        self._populate_mics(s.mic_device_index)
        self._populate_ollama_models(s.ollama_model)
        self._populate_openrouter_models(s.openrouter_model)
        self._update_key_display(s.openrouter_api_key)
        self.proxy_edit.setText(s.proxy_url or "")

        self.memory_check.setChecked(bool(s.memory_enabled))
        self._update_memory_info()

    def _populate_mics(self, selected_index: int | None) -> None:
        self.mic_combo.clear()
        try:
            devices = self._audio.list_input_devices()
        except Exception:
            devices = []
        for d in devices:
            self.mic_combo.addItem(f"[{d.index}] {d.name}", d.index)
        if selected_index is not None:
            pos = self.mic_combo.findData(selected_index)
            if pos >= 0:
                self.mic_combo.setCurrentIndex(pos)

    def _populate_ollama_models(self, current: str | None) -> None:
        self.ollama_model_combo.clear()
        models: list[str] = []
        provider = self._providers.get("ollama")
        if provider is not None:
            try:
                models = provider.list_models()
            except Exception:
                models = []
        if not models:
            models = [current or DEFAULT_OLLAMA_MODEL]
        self.ollama_model_combo.addItems(models)
        if current:
            self.ollama_model_combo.setCurrentText(current)

    def _populate_openrouter_models(self, current: str | None) -> None:
        self.openrouter_model_combo.clear()
        provider = self._providers.get("openrouter")
        models: list[str] = []
        if provider is not None and getattr(provider, "has_api_key", lambda: False)():
            try:
                models = provider.list_models()
            except Exception:
                models = []
        if not models:
            models = [current or DEFAULT_OPENROUTER_MODEL]
        self.openrouter_model_combo.addItems(models)
        if current:
            self.openrouter_model_combo.setCurrentText(current)

    def _update_key_display(self, key: str | None) -> None:
        if key:
            self.key_label.setText(
                self._i18n.t("settings_key_set", masked=_mask_key(key))
            )
        else:
            self.key_label.setText(self._i18n.t("settings_key_unset"))

    def _on_clear_key(self) -> None:
        self._clear_key_flag = True
        self.key_edit.clear()
        self.key_label.setText(self._i18n.t("settings_key_unset"))

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        provider_id = self.provider_combo.currentData()
        key_text = self.key_edit.text().strip()

        if provider_id == "openrouter":
            existing = self._settings.get("openrouter_api_key")
            effective_key = key_text or (
                None if self._clear_key_flag else existing
            )
            if not effective_key:
                QMessageBox.warning(
                    self,
                    self._i18n.t("settings_title"),
                    self._i18n.t("settings_openrouter_requires_key"),
                )
                return

        self._settings.set("language", self.lang_combo.currentData())
        self._settings.set("send_mode", self.send_mode_combo.currentData())
        self._settings.set("llm_provider", provider_id)

        mic_index = self.mic_combo.currentData()
        if mic_index is not None:
            self._settings.set("mic_device_index", mic_index)
            try:
                self._settings.set(
                    "mic_device_name", self._audio.get_device(mic_index).name
                )
            except Exception:
                pass

        ollama_model = self.ollama_model_combo.currentText().strip()
        if ollama_model:
            self._settings.set("ollama_model", ollama_model)

        if key_text:
            self._settings.set("openrouter_api_key", key_text)
        elif self._clear_key_flag:
            self._settings.set("openrouter_api_key", None)

        or_model = self.openrouter_model_combo.currentText().strip()
        if or_model:
            self._settings.set("openrouter_model", or_model)

        proxy = self.proxy_edit.text().strip() or None
        self._settings.set("proxy_url", proxy)
        self._http.set_proxy(proxy)

        self._settings.set("memory_enabled", self.memory_check.isChecked())

        self._settings.save()

        self._apply_runtime_changes(provider_id)
        QMessageBox.information(
            self,
            self._i18n.t("settings_title"),
            self._i18n.t("settings_saved")
            + "\n\n"
            + self._i18n.t("settings_restart_required"),
        )
        self.accept()

    def _apply_runtime_changes(self, provider_id: str) -> None:
        openrouter = self._providers.get("openrouter")
        if openrouter is not None and hasattr(openrouter, "set_api_key"):
            openrouter.set_api_key(self._settings.get("openrouter_api_key"))

        provider = self._providers.get(provider_id)
        if provider is None or not provider.is_available():
            provider = self._providers.get("ollama") or self._providers.default()
            provider_id = provider.provider_id

        if provider_id == "openrouter":
            model = self._settings.get("openrouter_model") or DEFAULT_OPENROUTER_MODEL
        else:
            model = self._settings.get("ollama_model") or DEFAULT_OLLAMA_MODEL

        self._conversation.set_provider(provider, model)

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def _update_memory_info(self) -> None:
        try:
            count = self._memory.count()
        except Exception:
            count = 0
        self.memory_info.setText(
            self._i18n.t("settings_memory_count", count=count)
        )

    def _on_clear_memory(self) -> None:
        reply = QMessageBox.question(
            self,
            self._i18n.t("settings_memory_clear"),
            self._i18n.t("settings_memory_clear_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self._memory.clear()
        except Exception as exc:
            QMessageBox.critical(self, self._i18n.t("error"), str(exc))
            return
        self._update_memory_info()

    # ------------------------------------------------------------------
    # Factory reset
    # ------------------------------------------------------------------

    def _on_factory_reset(self) -> None:
        reply = QMessageBox.question(
            self,
            self._i18n.t("settings_factory_reset"),
            self._i18n.t("settings_factory_reset_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        script = self._root / "reset_app.py"
        if not script.is_file():
            QMessageBox.critical(
                self,
                self._i18n.t("error"),
                f"{self._i18n.t('settings_reset_failed')}\n{script}",
            )
            return

        try:
            subprocess.Popen(
                [sys.executable, str(script), "--yes"],
                cwd=str(self._root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._i18n.t("error"),
                f"{self._i18n.t('settings_reset_failed')}\n{exc}",
            )
            return

        self.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)