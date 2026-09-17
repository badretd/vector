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
        "settings_title": "Settings",
        "settings_language": "Interface language",
        "settings_llm_provider": "LLM provider",
        "settings_ollama_model": "Ollama model",
        "settings_openrouter_key": "OpenRouter API key",
        "settings_openrouter_model": "OpenRouter model",
        "settings_proxy": "Proxy URL",
        "settings_proxy_placeholder": "http://user:pass@host:port (leave empty to disable)",
        "settings_clear_key": "Clear",
        "settings_key_set": "Current key: {masked}",
        "settings_key_unset": "No key set",
        "settings_factory_reset": "Factory reset",
        "settings_factory_reset_confirm": (
            "Reset Vector Voice to factory settings?\n\n"
            "The application will close and the reset script will run. "
            "You will see the first-time setup wizard on next launch."
        ),
        "settings_saved": "Settings saved.",
        "settings_restart_required": (
            "Language and microphone changes take effect after restart."
        ),
        "settings_openrouter_requires_key": (
            "OpenRouter is selected but no API key is set."
        ),
        "settings_reset_failed": "Failed to launch reset script:",
        "settings_memory_header": "Memory",
        "settings_memory_enabled": "Remember conversations",
        "settings_memory_count": "{count} item(s) stored",
        "settings_memory_clear": "Clear memory",
        "settings_memory_clear_confirm": (
            "Permanently delete all stored memories?\n\n"
            "Application settings are not affected."
        ),
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
        "settings_title": "Настройки",
        "settings_language": "Язык интерфейса",
        "settings_llm_provider": "LLM-провайдер",
        "settings_ollama_model": "Модель Ollama",
        "settings_openrouter_key": "API-ключ OpenRouter",
        "settings_openrouter_model": "Модель OpenRouter",
        "settings_proxy": "Прокси",
        "settings_proxy_placeholder": "http://user:pass@host:port (пусто — без прокси)",
        "settings_clear_key": "Очистить",
        "settings_key_set": "Текущий ключ: {masked}",
        "settings_key_unset": "Ключ не задан",
        "settings_factory_reset": "Сброс до заводских",
        "settings_factory_reset_confirm": (
            "Сбросить Vector Voice до заводских настроек?\n\n"
            "Приложение закроется и запустится скрипт сброса. "
            "При следующем запуске появится мастер первоначальной настройки."
        ),
        "settings_saved": "Настройки сохранены.",
        "settings_restart_required": (
            "Смена языка и микрофона вступит в силу после перезапуска."
        ),
        "settings_openrouter_requires_key": (
            "Выбран OpenRouter, но API-ключ не задан."
        ),
        "settings_reset_failed": "Не удалось запустить скрипт сброса:",
        "settings_memory_header": "Память",
        "settings_memory_enabled": "Запоминать разговоры",
        "settings_memory_count": "Сохранено записей: {count}",
        "settings_memory_clear": "Очистить память",
        "settings_memory_clear_confirm": (
            "Полностью удалить всю сохранённую память?\n\n"
            "Настройки приложения это не затрагивает."
        ),
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