"""First-run setup wizard: language -> Vosk model -> Ollama -> microphone."""
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox

import config
from core import i18n
from core.i18n import t
from core.ollama_helper import is_ollama_running, list_ollama_models
from core.vosk_model import install_vosk_model, vosk_model_ok


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_setup(settings, project_root: Path):
    """Run the full first-time setup.

    Returns a tuple (ok, device_index). `ok=False` means the user cancelled.
    """
    lang = _choose_language(settings.get("language") or "en")
    if lang is None:
        return False, None
    settings["language"] = lang
    i18n.set_language(lang)

    model_dir = project_root / settings.get("vosk_model_dir", "model")
    if not _ensure_vosk_model(project_root, model_dir):
        return False, None

    if not _setup_ollama(settings):
        return False, None

    device_index = _choose_microphone(settings)
    if device_index is None:
        return False, None

    settings["setup_complete"] = True
    settings.save()
    return True, device_index


def resolve_microphone(settings):
    """Return a currently valid device index for the saved microphone.

    Returns None when the caller must ask the user again:
      * remember_mic is False;
      * the saved index no longer refers to the same device and no match
        by name exists;
      * sounddevice cannot enumerate devices.
    """
    if not settings.get("remember_mic", True):
        return None

    saved_index = settings.get("mic_device_index")
    saved_name = settings.get("mic_device_name")
    if saved_index is None and not saved_name:
        return None

    try:
        import sounddevice as sd
        devices = sd.query_devices()
    except Exception:
        return None

    def is_input(d):
        return d and d.get("max_input_channels", 0) > 0

    # Same index and matching name (or no name stored).
    if isinstance(saved_index, int) and 0 <= saved_index < len(devices):
        dev = devices[saved_index]
        if is_input(dev) and (not saved_name or dev["name"] == saved_name):
            return saved_index

    # Index shifted — try to find the device by name.
    if saved_name:
        for i, d in enumerate(devices):
            if is_input(d) and d["name"] == saved_name:
                settings["mic_device_index"] = i
                return i

    # Device no longer present or turned into an output-only device.
    return None


def choose_microphone_dialog(settings):
    """Startup re-prompt: pick a device only, no "remember?" question.

    The existing `remember_mic` flag is preserved.
    """
    index = _pick_mic_index()
    if index is None:
        return None
    _store_mic(settings, index)
    if settings.get("remember_mic", True):
        settings.save()
    return index


# ---------------------------------------------------------------------------
# Setup steps
# ---------------------------------------------------------------------------

def _choose_language(default: str):
    box = QMessageBox()
    box.setWindowTitle("Language / Язык")
    box.setText("Choose interface language:\nВыберите язык интерфейса:")
    ru_btn = box.addButton("Русский", QMessageBox.AcceptRole)
    en_btn = box.addButton("English", QMessageBox.AcceptRole)
    box.setDefaultButton(en_btn if default != "ru" else ru_btn)
    box.exec_()
    clicked = box.clickedButton()
    if clicked is ru_btn:
        return "ru"
    if clicked is en_btn:
        return "en"
    return None


def _ensure_vosk_model(project_root: Path, model_dir: Path) -> bool:
    if vosk_model_ok(model_dir):
        return True

    data_dir = project_root / "data"
    archives = sorted(data_dir.glob("vosk-model-*.zip")) if data_dir.is_dir() else []

    if not archives:
        QMessageBox.warning(
            None, t("vosk_model_missing_title"),
            t("vosk_zip_not_found") + f"\n{data_dir}",
        )
        return True

    reply = QMessageBox.question(
        None, t("vosk_model_missing_title"),
        t("vosk_model_missing_msg"),
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return True

    names = [a.name for a in archives]
    choice, ok = QInputDialog.getItem(
        None, t("setup_title"), t("vosk_select_archive"),
        names, 0, False,
    )
    if not ok:
        return False

    try:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        install_vosk_model(data_dir / choice, model_dir)
        QApplication.restoreOverrideCursor()
    except Exception as e:
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(
            None, t("error"), f"{t('vosk_model_failed')}\n{e}",
        )
        return False

    QMessageBox.information(None, t("setup_title"), t("vosk_model_installed"))
    return True


def _setup_ollama(settings) -> bool:
    while True:
        if not is_ollama_running():
            box = QMessageBox()
            box.setWindowTitle(t("ollama_not_found_title"))
            box.setText(t("ollama_not_found_msg"))
            retry_btn = box.addButton(t("ollama_retry"), QMessageBox.AcceptRole)
            box.addButton(t("ollama_skip"), QMessageBox.RejectRole)
            box.exec_()
            if box.clickedButton() is retry_btn:
                continue
            settings["ollama_model"] = config.DEFAULT_OLLAMA_MODEL
            return True

        models = list_ollama_models()
        if not models:
            box = QMessageBox()
            box.setWindowTitle(t("ollama_model_title"))
            box.setText(t("ollama_no_models"))
            box.addButton(t("skip"), QMessageBox.AcceptRole)
            box.exec_()
            settings["ollama_model"] = config.DEFAULT_OLLAMA_MODEL
            return True

        current = settings.get("ollama_model") or models[0]
        try:
            idx = models.index(current)
        except ValueError:
            idx = 0

        choice, ok = QInputDialog.getItem(
            None, t("ollama_model_title"),
            t("ollama_model_prompt"), models, idx, False,
        )
        if not ok:
            return False
        settings["ollama_model"] = choice
        return True


# ---------------------------------------------------------------------------
# Microphone helpers
# ---------------------------------------------------------------------------

def _pick_mic_index():
    """Show the input-device list. Return index or None if cancelled/empty."""
    import sounddevice as sd
    devices = sd.query_devices()
    inputs = [(i, d) for i, d in enumerate(devices) if d["max_input_channels"] > 0]

    if not inputs:
        QMessageBox.critical(None, t("error"), t("mic_none"))
        return None

    labels = [f"[{i}] {d['name']}" for i, d in inputs]

    try:
        default_idx = sd.default.device[0]
    except Exception:
        default_idx = -1

    default_pos = 0
    for pos, (i, _) in enumerate(inputs):
        if i == default_idx:
            default_pos = pos
            break

    choice, ok = QInputDialog.getItem(
        None, t("mic_select_title"), t("mic_select_prompt"),
        labels, default_pos, False,
    )
    if not ok:
        return None

    return inputs[labels.index(choice)][0]


def _store_mic(settings, index):
    """Save both index and device name in memory."""
    import sounddevice as sd
    try:
        name = sd.query_devices(index)["name"]
    except Exception:
        name = None
    settings["mic_device_index"] = index
    settings["mic_device_name"] = name


def _choose_microphone(settings):
    """Setup-time: pick a device and ask whether to remember it.

    Nothing is written to disk here — run_setup() saves at the very end.
    """
    index = _pick_mic_index()
    if index is None:
        return None
    _store_mic(settings, index)

    box = QMessageBox()
    box.setWindowTitle(t("mic_select_title"))
    box.setText(t("mic_remember"))
    yes_btn = box.addButton(t("mic_remember_yes"), QMessageBox.AcceptRole)
    box.addButton(t("mic_remember_no"), QMessageBox.RejectRole)
    box.exec_()
    settings["remember_mic"] = box.clickedButton() is yes_btn

    return index