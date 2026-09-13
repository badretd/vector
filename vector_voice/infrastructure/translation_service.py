"""Dictionary-based translation service (RU / EN)."""
from __future__ import annotations

from typing import Any

from vector_voice.domain.ports import TranslationServicePort

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Vector Voice",
        "language_prompt": "Choose interface language:",
        "setup_title": "First-time setup",
        "vosk_model_missing_title": "Vosk model not found",
        "vosk_model_missing_msg": "The speech recognition model is missing. "
                                  "Install a built-in model now?",
        "vosk_select_archive": "Pick a model archive to install:",
        "vosk_model_installed": "Vosk model installed.",
        "vosk_model_failed": "Failed to install Vosk model:",
        "vosk_zip_not_found": "No Vosk archives found in:",
        "ollama_not_found_title": "Ollama is not running",
        "ollama_not_found_msg": (
            "Ollama is not installed or not running.\n\n"
            "1. Download from https://ollama.com/download\n"
            "2. Install and start Ollama (it listens on http://localhost:11434)\n"
            "3. Then press Retry."
        ),
        "ollama_retry": "Retry",
        "ollama_skip": "Skip",
        "ollama_model_title": "Choose Ollama model",
        "ollama_model_prompt": "Select the LLM model to use:",
        "ollama_no_models": "No Ollama models found.\n"
                            "Pull one first, for example:\n"
                            "    ollama pull phi3:mini",
        "mic_select_title": "Microphone",
        "mic_select_prompt": "Select input device:",
        "mic_remember": "Remember this choice?",
        "mic_remember_yes": "Yes, remember",
        "mic_remember_no": "No, ask each time",
        "mic_none": "No input devices found.",
        "skip": "Skip",
        "yes": "Yes",
        "no": "No",
        "error": "Error",
        "setup_cancelled": "Setup cancelled.",
        "placeholder_subtitle": "Start speaking",
        "send_hint": "Press Enter to send the text",
        "settings_tooltip": "Settings",
        "settings_send_mode_header": "Send mode",
        "settings_send_enter": "Send by Enter",
        "settings_send_timer": "Send by timer (3 sec)",
    },
    "ru": {
        "app_title": "Vector Voice",
        "language_prompt": "Выберите язык интерфейса:",
        "setup_title": "Первоначальная настройка",
        "vosk_model_missing_title": "Модель Vosk не найдена",
        "vosk_model_missing_msg": "Речевая модель отсутствует. "
                                  "Установить встроенную модель сейчас?",
        "vosk_select_archive": "Выберите архив модели для установки:",
        "vosk_model_installed": "Модель Vosk установлена.",
        "vosk_model_failed": "Не удалось установить модель Vosk:",
        "vosk_zip_not_found": "Архивы Vosk не найдены в:",
        "ollama_not_found_title": "Ollama не запущена",
        "ollama_not_found_msg": (
            "Ollama не установлена или не запущена.\n\n"
            "1. Скачайте с https://ollama.com/download\n"
            "2. Установите и запустите Ollama (слушает http://localhost:11434)\n"
            "3. Нажмите «Повторить»."
        ),
        "ollama_retry": "Повторить",
        "ollama_skip": "Пропустить",
        "ollama_model_title": "Выбор модели Ollama",
        "ollama_model_prompt": "Выберите языковую модель:",
        "ollama_no_models": "Модели Ollama не найдены.\n"
                            "Сначала загрузите модель, например:\n"
                            "    ollama pull phi3:mini",
        "mic_select_title": "Микрофон",
        "mic_select_prompt": "Выберите устройство ввода:",
        "mic_remember": "Запомнить выбор микрофона?",
        "mic_remember_yes": "Да, запомнить",
        "mic_remember_no": "Нет, спрашивать каждый раз",
        "mic_none": "Устройства ввода не найдены.",
        "skip": "Пропустить",
        "yes": "Да",
        "no": "Нет",
        "error": "Ошибка",
        "setup_cancelled": "Настройка отменена.",
        "placeholder_subtitle": "Начни говорить",
        "send_hint": "Нажми Enter чтобы отправить текст",
        "settings_tooltip": "Настройки",
        "settings_send_mode_header": "Способ отправки",
        "settings_send_enter": "Отправка по Enter",
        "settings_send_timer": "Отправка по таймеру (3 сек)",
    },
}


class DictTranslationService(TranslationServicePort):
    def __init__(self, lang: str = "en") -> None:
        self._lang = lang if lang in TEXTS else "en"

    def set_language(self, code: str) -> None:
        self._lang = code if code in TEXTS else "en"

    def get_language(self) -> str:
        return self._lang

    def t(self, key: str, **kwargs: Any) -> str:
        s = TEXTS.get(self._lang, {}).get(key) or TEXTS["en"].get(key, key)
        if kwargs:
            try:
                s = s.format(**kwargs)
            except Exception:
                pass
        return s