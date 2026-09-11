"""Background thread that captures microphone audio and feeds it to Vosk."""
import json
import queue
import sys
from math import gcd

import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QThread, pyqtSignal
from scipy.signal import resample_poly
from vosk import Model, KaldiRecognizer

import config
from config import CHUNK_SIZE, TARGET_RATE
from core.audio_devices import pick_samplerate


class SpeechThread(QThread):
    """Continuously listens on the mic and emits recognized text."""

    text_recognized = pyqtSignal(str)

    def __init__(self, device_index):
        super().__init__()
        self._running = True
        self._reset_flag = False
        self._need_reset = False
        self._enabled = True
        self._final_text = ""
        self.audio_queue = queue.Queue()
        self.device_index = device_index
        self.actual_rate = TARGET_RATE
        self.resample_up = 1
        self.resample_down = 1

    def run(self):
        model = Model(config.MODEL_PATH)
        rec = KaldiRecognizer(model, TARGET_RATE)

        self.actual_rate = pick_samplerate(self.device_index)
        g = gcd(TARGET_RATE, self.actual_rate)
        self.resample_up = TARGET_RATE // g
        self.resample_down = self.actual_rate // g

        try:
            with sd.RawInputStream(
                samplerate=self.actual_rate,
                blocksize=CHUNK_SIZE,
                dtype="int16",
                channels=1,
                device=self.device_index,
                callback=self._audio_callback,
            ):
                while self._running:
                    if self._reset_flag:
                        self._final_text = ""
                        self._reset_flag = False

                    if self._need_reset:
                        rec.Reset()
                        self._final_text = ""
                        self._need_reset = False

                    try:
                        data = self.audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    if not self._enabled:
                        continue

                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip()
                        if text:
                            self._final_text += (" " if self._final_text else "") + text
                            self.text_recognized.emit(self._final_text)
                    else:
                        partial = json.loads(rec.PartialResult())
                        partial_text = partial.get("partial", "").strip()
                        if partial_text:
                            combined = self._final_text
                            if combined:
                                combined += " "
                            combined += partial_text
                            self.text_recognized.emit(combined)
        except Exception as e:
            print(f"Audio error: {e}")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)

        raw = bytes(indata)
        if self.actual_rate != TARGET_RATE:
            arr = np.frombuffer(raw, dtype=np.int16)
            resampled = resample_poly(arr, self.resample_up, self.resample_down)
            raw = resampled.astype(np.int16).tobytes()

        self.audio_queue.put(raw)

    def reset(self):
        self._reset_flag = True
        self._need_reset = True

    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self._need_reset = True

    def stop(self):
        self._running = False
        self.wait()