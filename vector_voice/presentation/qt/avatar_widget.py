"""Sprite-based avatar widget.

The widget is intentionally a thin shell around ``AvatarRendererPort`` so a
vector renderer can be plugged in later without touching the main window.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel

from vector_voice.domain.ports import AssetRepositoryPort


class SpriteAvatarWidget(QLabel):
    """Avatar rendered from pixel-art sprites, scaled with nearest-neighbour."""

    def __init__(self, assets: AssetRepositoryPort, source_size: int, scale: int) -> None:
        super().__init__()
        self._assets = assets
        self._source_size = source_size
        self._base_size = source_size * scale
        self._emotion: str | None = None
        self._user_scale = 1.0

        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: transparent;")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update_size()

    # -- AvatarRendererPort-ish API ---------------------------------------

    def set_emotion(self, emotion: str | None) -> None:
        self._emotion = emotion
        self.refresh()

    def set_scale(self, scale: float) -> None:
        self._user_scale = scale
        self._update_size()

    def refresh(self) -> None:
        if not self._emotion:
            self.clear()
            return
        pix = self._assets.emotion_source_pixmap(self._emotion)
        if pix is None:
            self.clear()
            return
        size = self.display_size()
        self.setPixmap(
            pix.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        )

    def display_size(self) -> int:
        return max(24, int(self._base_size * self._user_scale))

    # -- internals --------------------------------------------------------

    def _update_size(self) -> None:
        size = self.display_size()
        self.setFixedSize(size, size)
        self.refresh()