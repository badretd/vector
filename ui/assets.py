"""Pixmap loaders for emotion sprites and the microphone icon."""

import math
import os

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QPixmap

from config import (
    EMOTIONS,
    EMOTIONS_DIR,
    EMOTION_DISPLAY_SIZE,
    MIC_DISPLAY_SIZE,
    MIC_OFF_PATH,
)


def load_emotion_pixmaps():
    """Load all emotion sprites and upscale them without smoothing.

    Nearest-neighbour scaling (Qt.FastTransformation) preserves the
    pixel-art look — bilinear filtering would blur 12×12 sprites badly.
    """
    pixmaps = {}
    for name in EMOTIONS:
        path = os.path.join(EMOTIONS_DIR, f"{name}.png")
        if not os.path.exists(path):
            print(f"[emotions] Missing file: {path}")
            continue
        src = QPixmap(path)
        if src.isNull():
            print(f"[emotions] Failed to load: {path}")
            continue
        scaled = src.scaled(
            EMOTION_DISPLAY_SIZE,
            EMOTION_DISPLAY_SIZE,
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation,
        )
        pixmaps[name] = scaled
    return pixmaps


def load_mic_off_pixmap():
    """Load assets/mic_off.png and upscale it ×12 without smoothing.

    Nearest-neighbour scaling (Qt.FastTransformation) keeps the pixel-art
    look intact — same approach as for emotion sprites.
    """
    if not os.path.exists(MIC_OFF_PATH):
        print(f"[mic] Missing file: {MIC_OFF_PATH}")
        return None
    src = QPixmap(MIC_OFF_PATH)
    if src.isNull():
        print(f"[mic] Failed to load: {MIC_OFF_PATH}")
        return None
    return src.scaled(
        MIC_DISPLAY_SIZE,
        MIC_DISPLAY_SIZE,
        Qt.IgnoreAspectRatio,
        Qt.FastTransformation,
    )

def make_settings_pixmap(size=128):
    """Render a simple hamburger icon used for the settings menu button."""
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

def load_emotion_source_pixmaps():
    """Load raw (unscaled) emotion sprites so callers can re-scale on zoom."""
    pixmaps = {}
    for name in EMOTIONS:
        path = os.path.join(EMOTIONS_DIR, f"{name}.png")
        if not os.path.exists(path):
            print(f"[emotions] Missing file: {path}")
            continue
        src = QPixmap(path)
        if src.isNull():
            print(f"[emotions] Failed to load: {path}")
            continue
        pixmaps[name] = src
    return pixmaps


def load_mic_off_source_pixmap():
    """Load raw (unscaled) mic_off.png so callers can re-scale on zoom."""
    if not os.path.exists(MIC_OFF_PATH):
        print(f"[mic] Missing file: {MIC_OFF_PATH}")
        return None
    src = QPixmap(MIC_OFF_PATH)
    if src.isNull():
        print(f"[mic] Failed to load: {MIC_OFF_PATH}")
        return None
    return src