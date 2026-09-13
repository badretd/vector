"""Vosk-backed speech recognition running in a background QThread.

Implements the ``SpeechRecognizerPort`` protocol structurally; it does NOT
inherit from the port because QObject uses its own metaclass.
"""
from __future__ import annotations

import json
import queue
import sys
from math import gcd
from typing import Callable

import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from scipy.signal import resample_poly
from vosk import KaldiRecognizer, Model

from vector_voice.application.constants import AUDIO_CHUNK_SIZE, TARGET_AUDIO_RATE


class _SpeechWorker(QThread):
    """QThread that reads from the microphone and runs Vosk recognition."""

    text_ready = pyqtSignal(str)

    def __init__(self, model_path: str, device_index: int, actual_rate: int) -> None:
        super().__init__()
        self._model_path = model_path
        self._device_index = device_index
        self._actual_rate = actual_rate
        self._running = True
        self._enabled = True
        self._reset_requested = False
        self._final_text = ""
        self._queue: queue.Queue[bytes] = queue.Queue()

    # -- QThread entry -----------------------------------------------------

    def run(self) -> None:
        try:
            model = Model(self._model_path)
        except Exception as exc:
            print(f"Failed to load Vosk model: {exc}")
            return

        rec = KaldiRecognizer(model, TARGET_AUDIO_RATE)
        g = gcd(TARGET_AUDIO_RATE, self._actual_rate)
        up = TARGET_AUDIO_RATE // g
        down = self._actual_rate // g

        try:
            with sd.RawInputStream(
                samplerate=self._actual_rate,
                blocksize=AUDIO_CHUNK_SIZE,
                dtype="int16",
                channels=1,
                device=self._device_index,
                callback=self._on_audio,
            ):
                while self._running:
                    if self._reset_requested:
                        rec.Reset()
                        self._final_text = ""
                        self._reset_requested = False

                    try:
                        data = self._queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    if not self._enabled:
                        continue

                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip()
                        if text:
                            sep = " " if self._final_text else ""
                            self._final_text += sep + text
                            self.text_ready.emit(self._final_text)
                    else:
                        partial = json.loads(rec.PartialResult())
                        partial_text = partial.get("partial", "").strip()
                        if partial_text:
                            combined = self._final_text
                            if combined:
                                combined += " "
                            combined += partial_text
                            self.text_ready.emit(combined)
        except Exception as exc:
            print(f"Audio error: {exc}")

    def _on_audio(self, indata, frames, time_info, status) -> None:
        if status:
            print(status, file=sys.stderr)

        raw = bytes(indata)
        if self._actual_rate != TARGET_AUDIO_RATE:
            arr = np.frombuffer(raw, dtype=np.int16)
            g = gcd(TARGET_AUDIO_RATE, self._actual_rate)
            resampled = resample_poly(
                arr, TARGET_AUDIO_RATE // g, self._actual_rate // g
            )
            raw = resampled.astype(np.int16).tobytes()

        self._queue.put(raw)

    # -- controls ----------------------------------------------------------

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._reset_requested = True

    def request_reset(self) -> None:
        self._reset_requested = True

    def stop(self) -> None:
        self._running = False
        self.wait()


class VoskSpeechAdapter(QObject):
    """Thread-safe wrapper exposing a callback-based API.

    Structurally satisfies ``SpeechRecognizerPort`` without inheriting it.
    """

    text_recognized = pyqtSignal(str)

    def __init__(self, model_path: str, device_index: int, actual_rate: int) -> None:
        super().__init__()
        self._worker = _SpeechWorker(model_path, device_index, actual_rate)
        self._worker.text_ready.connect(self.text_recognized)

    def set_text_callback(self, callback: Callable[[str], None]) -> None:
        self.text_recognized.connect(callback)

    def start(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        self._worker.stop()

    def reset(self) -> None:
        self._worker.request_reset()

    def set_enabled(self, enabled: bool) -> None:
        self._worker.set_enabled(enabled)