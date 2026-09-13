"""sounddevice-backed implementation of AudioDevicePort."""
from __future__ import annotations

import sounddevice as sd

from vector_voice.application.constants import TARGET_AUDIO_RATE
from vector_voice.domain.models import MicrophoneInfo
from vector_voice.domain.ports import AudioDevicePort


class SounddeviceAudioAdapter(AudioDevicePort):
    def list_input_devices(self) -> list[MicrophoneInfo]:
        devices = sd.query_devices()
        try:
            default_index = sd.default.device[0]
        except Exception:
            default_index = -1

        result: list[MicrophoneInfo] = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                result.append(
                    MicrophoneInfo(
                        index=i,
                        name=d["name"],
                        default_samplerate=float(d["default_samplerate"]),
                        is_default=(i == default_index),
                        max_input_channels=int(d["max_input_channels"]),
                    )
                )
        return result

    def default_input_index(self) -> int | None:
        try:
            idx = sd.default.device[0]
            return idx if idx is not None and idx >= 0 else None
        except Exception:
            return None

    def get_device(self, index: int) -> MicrophoneInfo:
        d = sd.query_devices(index)
        try:
            default_index = sd.default.device[0]
        except Exception:
            default_index = -1
        return MicrophoneInfo(
            index=index,
            name=d["name"],
            default_samplerate=float(d["default_samplerate"]),
            is_default=(index == default_index),
            max_input_channels=int(d["max_input_channels"]),
        )

    def check_samplerate(self, index: int, rate: int) -> bool:
        try:
            sd.check_input_settings(
                device=index, samplerate=rate, dtype="int16", channels=1
            )
            return True
        except Exception:
            return False

    def pick_samplerate(self, index: int) -> int:
        """Return TARGET_AUDIO_RATE if supported, otherwise device default."""
        if self.check_samplerate(index, TARGET_AUDIO_RATE):
            return TARGET_AUDIO_RATE
        return int(self.get_device(index).default_samplerate)