"""Application entry point."""

import sys

from PyQt5.QtWidgets import QApplication
from vosk import SetLogLevel

from core.audio_devices import choose_input_device
from ui.main_window import VoiceWindow

SetLogLevel(-1)


def main():
    device_index = choose_input_device()
    app = QApplication(sys.argv)
    window = VoiceWindow(device_index)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()