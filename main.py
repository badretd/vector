"""Application entry point."""
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from vosk import SetLogLevel

import config
from core import i18n
from core.settings import Settings
from ui.setup_wizard import (
    choose_microphone_dialog,
    resolve_microphone,
    run_setup,
)

SetLogLevel(-1)


def main():
    project_root = Path(__file__).resolve().parent

    app = QApplication(sys.argv)

    settings = Settings()
    i18n.set_language(settings.get("language") or "en")

    if not settings.get("setup_complete"):
        # First launch: the wizard already picks a microphone and returns it.
        ok, device_index = run_setup(settings, project_root)
        if not ok:
            print(i18n.t("setup_cancelled"))
            return
    else:
        # On later launches, reuse the saved microphone when it is still
        # available. Otherwise ask once for this session only.
        device_index = resolve_microphone(settings)
        if device_index is None:
            device_index = choose_microphone_dialog(settings)
            if device_index is None:
                return

    # Apply runtime overrides only after settings are final.
    config.MODEL_PATH = str(project_root / settings.get("vosk_model_dir", "model"))
    config.OLLAMA_MODEL = (
        settings.get("ollama_model") or config.DEFAULT_OLLAMA_MODEL
    )

    from ui.main_window import VoiceWindow
    window = VoiceWindow(device_index)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()