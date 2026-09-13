"""Qt-backed asset loader. Returns QPixmap for the presentation layer."""
from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainter, QPen, QPixmap

from vector_voice.domain.models import Emotion
from vector_voice.domain.ports import AssetRepositoryPort


class QtAssetRepository(AssetRepositoryPort):
    def __init__(self, assets_dir: Path, emotions_dir: Path) -> None:
        self._assets = assets_dir
        self._emotions = emotions_dir
        self._emotion_cache: dict[str, QPixmap] = {}
        self._mic_cache: QPixmap | None = None

    def emotion_source_pixmap(self, emotion: str) -> QPixmap | None:
        if emotion in self._emotion_cache:
            return self._emotion_cache[emotion]
        path = os.path.join(self._emotions, f"{emotion}.png")
        if not os.path.exists(path):
            print(f"[emotions] Missing file: {path}")
            return None
        pix = QPixmap(path)
        if pix.isNull():
            print(f"[emotions] Failed to load: {path}")
            return None
        self._emotion_cache[emotion] = pix
        return pix

    def mic_off_source_pixmap(self) -> QPixmap | None:
        if self._mic_cache is not None:
            return self._mic_cache
        path = self._assets / "mic_off.png"
        if not path.exists():
            print(f"[mic] Missing file: {path}")
            return None
        pix = QPixmap(str(path))
        if pix.isNull():
            print(f"[mic] Failed to load: {path}")
            return None
        self._mic_cache = pix
        return pix

    def settings_icon(self, size: int) -> QPixmap:
        """Render a simple hamburger icon at the requested size."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(Qt.white)
        pen.setWidthF(size * 0.10)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        margin = size * 0.22
        for i in range(3):
            y = size * (0.30 + i * 0.20)
            p.drawLine(QPointF(margin, y), QPointF(size - margin, y))

        p.end()
        return pixmap