"""Pixmap loaders for emotion sprites and the microphone icon."""

import math
import os

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QPixmap

from config import EMOTIONS, EMOTIONS_DIR, EMOTION_DISPLAY_SIZE


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


def make_mic_pixmap(size=128, crossed=False):
    """Render the microphone icon (optionally with a diagonal strike)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing, True)

    pen = QPen(Qt.white)
    pen.setWidthF(size * 0.06)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    cx = size / 2.0

    # Capsule (the mic body)
    cap_w = size * 0.28
    cap_h = size * 0.42
    cap_x = (size - cap_w) / 2.0
    cap_y = size * 0.05
    p.drawRoundedRect(QRectF(cap_x, cap_y, cap_w, cap_h),
                      cap_w / 2.0, cap_w / 2.0)

    # Semicircular arc around the capsule
    arc_cx = cx
    arc_cy = size * 0.36
    arc_r = size * 0.22

    path = QPainterPath()
    steps = 80
    for i in range(steps + 1):
        theta = math.pi * i / steps
        x = arc_cx + arc_r * math.cos(theta)
        y = arc_cy + arc_r * math.sin(theta)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    p.drawPath(path)

    # Stem and base
    stem_top = arc_cy + arc_r
    stem_bottom = size * 0.88
    p.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bottom))

    base_half = size * 0.15
    p.drawLine(QPointF(cx - base_half, stem_bottom),
               QPointF(cx + base_half, stem_bottom))

    if crossed:
        pen_cross = QPen(Qt.white)
        pen_cross.setWidthF(size * 0.08)
        pen_cross.setCapStyle(Qt.RoundCap)
        p.setPen(pen_cross)
        p.drawLine(QPointF(size * 0.15, size * 0.15),
                   QPointF(size * 0.85, size * 0.85))

    p.end()
    return pixmap

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