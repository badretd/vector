"""Theme tokens and manager. Only one theme is shipped, but the API is
ready for theme switching."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    window_bg: str = "#000000"
    text_primary: str = "#ffffff"
    text_user: str = "#ffff00"
    text_hint: str = "#ffcc00"
    text_subtitle: str = "#888888"

    menu_bg: str = "#1e1e1e"
    menu_fg: str = "#ffffff"
    menu_border: str = "#444444"
    menu_selected_bg: str = "#333333"
    menu_disabled_fg: str = "#888888"

    font_family: str = "Arial"
    normal_font_size: int = 28
    placeholder_font_size: int = 56
    subtitle_font_size: int = 18
    hint_font_size: int = 20

    # Emotion sprite sizing (source px * scale).
    emotion_source_size: int = 12
    emotion_scale: int = 10
    mic_source_size: int = 12
    mic_scale: int = 4
    settings_icon_size: int = 40

    def placeholder_font_size_pt(self) -> float:
        return float(self.placeholder_font_size)


class QtThemeManager:
    """Applies theme tokens to Qt widgets. Currently uses one palette."""

    def __init__(self, tokens: ThemeTokens | None = None) -> None:
        self._tokens = tokens or ThemeTokens()

    def tokens(self) -> ThemeTokens:
        return self._tokens

    def apply(self, widget) -> None:
        widget.setStyleSheet(f"background-color: {self._tokens.window_bg};")

    def menu_stylesheet(self) -> str:
        t = self._tokens
        return (
            f"QMenu {{ background-color: {t.menu_bg}; color: {t.menu_fg}; "
            f"border: 1px solid {t.menu_border}; padding: 4px; }}"
            f"QMenu::item {{ padding: 6px 18px; }}"
            f"QMenu::item:selected {{ background-color: {t.menu_selected_bg}; }}"
            f"QMenu::item:disabled {{ color: {t.menu_disabled_fg}; }}"
            f"QMenu::separator {{ height: 1px; background: {t.menu_border}; margin: 4px 8px; }}"
        )