from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THEME_FILE = PACKAGE_ROOT / "data" / "themes.json"

THEME_KEYS = {
        "window_background",
        "base_background",
        "text_color",
        "group_background",
        "group_border",
        "group_title_color",
        "button_background",
        "button_text",
        "button_hover",
        "button_pressed",
        "button_disabled",
        "button_disabled_text",
        "input_background",
        "input_border",
        "input_focus_border",
        "select_background",
        "select_text",
        "table_background",
        "table_alternate",
        "table_grid",
        "header_background",
        "header_text",
        "status_background",
        "status_text",
        "scrollbar_background",
        "scrollbar_handle",
}

DEFAULT_THEME_NAME = "Sunny Breeze"

DEFAULT_THEME_DATA: Dict[str, object] = {
        "active_theme": DEFAULT_THEME_NAME,
        "themes": {
                DEFAULT_THEME_NAME: {
                        "window_background": "#c4ebf2",
                        "base_background": "#c4ebf2",
                        "text_color": "#2C2C2C",
                        "group_background": "#add9e6",
                        "group_border": "#88c7e6",
                        "group_title_color": "#4f7eb3",
                        "button_background": "#ffd302",
                        "button_text": "#2C2C2C",
                        "button_hover": "#fff683",
                        "button_pressed": "#ffffc1",
                        "button_disabled": "#add9e6",
                        "button_disabled_text": "#6F6F6F",
                        "input_background": "#FFFFFF",
                        "input_border": "#88c7e6",
                        "input_focus_border": "#ffd302",
                        "select_background": "#ffd302",
                        "select_text": "#2C2C2C",
                        "table_background": "#FFFFFF",
                        "table_alternate": "#add9e6",
                        "table_grid": "#add9e6",
                        "header_background": "#88c7e6",
                        "header_text": "#2C2C2C",
                        "status_background": "#ffd302",
                        "status_text": "#2C2C2C",
                        "scrollbar_background": "#add9e6",
                        "scrollbar_handle": "#ffd302",
                },
                "Aurora Dusk": {
                        "window_background": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a2a6c, stop:1 #3a1c71)",
                        "base_background": "transparent",
                        "text_color": "#f1f5ff",
                        "group_background": "#273b7a",
                        "group_border": "#3f4d8c",
                        "group_title_color": "#8fa2ff",
                        "button_background": "#ff6f61",
                        "button_text": "#ffffff",
                        "button_hover": "#ff8f7a",
                        "button_pressed": "#ff5a4a",
                        "button_disabled": "#3f4d8c",
                        "button_disabled_text": "#a8b2d6",
                        "input_background": "#1b2549",
                        "input_border": "#3f4d8c",
                        "input_focus_border": "#ff6f61",
                        "select_background": "#ff6f61",
                        "select_text": "#ffffff",
                        "table_background": "#1b2549",
                        "table_alternate": "#24315f",
                        "table_grid": "#3f4d8c",
                        "header_background": "#34407a",
                        "header_text": "#f1f5ff",
                        "status_background": "#ff6f61",
                        "status_text": "#ffffff",
                        "scrollbar_background": "#24315f",
                        "scrollbar_handle": "#ff6f61",
                },
        },
}


STYLESHEET_TEMPLATE = """
QMainWindow {{
        background: {window_background};
        color: {text_color};
}}

QWidget {{
        background: {base_background};
        color: {text_color};
}}

QLabel,
QStatusBar QLabel {{
        color: {text_color};
}}

QGroupBox {{
        background-color: {group_background};
        border: 1px solid {group_border};
        border-radius: 8px;
        margin-top: 12px;
        padding: 12px;
}}

QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 4px;
        color: {group_title_color};
        font-weight: 600;
}}

QPushButton,
QToolButton {{
        background-color: {button_background};
        color: {button_text};
        border: none;
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 600;
}}

QPushButton:hover,
QToolButton:hover {{
        background-color: {button_hover};
}}

QPushButton:pressed,
QToolButton:pressed {{
        background-color: {button_pressed};
}}

QPushButton:disabled,
QToolButton:disabled {{
        background-color: {button_disabled};
        color: {button_disabled_text};
}}

QLineEdit,
QComboBox,
QDateEdit {{
        background-color: {input_background};
        border: 1px solid {input_border};
        border-radius: 4px;
        padding: 4px 6px;
}}

QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus {{
        border: 1px solid {input_focus_border};
}}

QComboBox QAbstractItemView,
QDateEdit QAbstractItemView {{
        background-color: {input_background};
        border: 1px solid {input_border};
        selection-background-color: {select_background};
        selection-color: {select_text};
}}

QTableView {{
        background-color: {table_background};
        alternate-background-color: {table_alternate};
        gridline-color: {table_grid};
        border: 1px solid {table_grid};
        selection-background-color: {select_background};
        selection-color: {select_text};
}}

QTableView::item:selected {{
        background-color: {select_background};
        color: {select_text};
}}

QHeaderView::section {{
        background-color: {header_background};
        color: {header_text};
        padding: 8px;
        border: none;
        border-right: 1px solid {table_grid};
}}

QTableCornerButton::section {{
        background-color: {header_background};
        border: none;
}}

QStatusBar {{
        background-color: {status_background};
        color: {status_text};
        border-top: 1px solid {table_grid};
}}

QScrollBar:vertical,
QScrollBar:horizontal {{
        background: {scrollbar_background};
        border: none;
        border-radius: 4px;
        margin: 0px;
}}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {{
        background: {scrollbar_handle};
        border-radius: 4px;
        min-height: 20px;
        min-width: 20px;
}}

QScrollBar::add-line,
QScrollBar::sub-line {{
        background: none;
}}
"""


def _deep_copy_default_data() -> Dict[str, object]:
        return deepcopy(DEFAULT_THEME_DATA)


def _sanitize_theme_values(values: Mapping[str, object], fallback: Mapping[str, str]) -> Dict[str, str]:
        sanitized: Dict[str, str] = {}
        for key in THEME_KEYS:
                if key in values:
                        sanitized[key] = str(values[key])
                else:
                        sanitized[key] = str(fallback.get(key, fallback.get("text_color", "#000000")))
        return sanitized


@dataclass
class Theme:
        name: str
        values: Dict[str, str]

        def stylesheet(self) -> str:
                return STYLESHEET_TEMPLATE.format_map(self.values)


class ThemeManager:
        """Load and persist UI themes from a JSON configuration file."""

        def __init__(self, theme_file: Path | None = None) -> None:
                self.theme_file = theme_file or DEFAULT_THEME_FILE
                self._data: Dict[str, object] = {}
                self._load_or_create()

        # ------------------------------------------------------------------
        # Persistence helpers
        # ------------------------------------------------------------------
        def _load_or_create(self) -> None:
                if not self.theme_file.exists():
                        self.theme_file.parent.mkdir(parents=True, exist_ok=True)
                        self._data = _deep_copy_default_data()
                        self._save()
                        return

                try:
                        with self.theme_file.open("r", encoding="utf-8") as handle:
                                loaded = json.load(handle)
                except (OSError, json.JSONDecodeError):
                        self._data = _deep_copy_default_data()
                        self._save()
                        return

                self._data = self._merge_with_defaults(loaded)
                self._save()

        def _merge_with_defaults(self, raw_data: Mapping[str, object]) -> Dict[str, object]:
                merged: Dict[str, object] = {"themes": {}}
                raw_themes = raw_data.get("themes", {})
                if not isinstance(raw_themes, dict):
                        raw_themes = {}

                sanitized_themes: Dict[str, Dict[str, str]] = {}

                # preserve user defined order
                for name, values in raw_themes.items():
                        if not isinstance(values, Mapping):
                                continue
                        fallback = DEFAULT_THEME_DATA["themes"].get(name)  # type: ignore[index]
                        if not isinstance(fallback, Mapping):
                                fallback = DEFAULT_THEME_DATA["themes"][DEFAULT_THEME_NAME]  # type: ignore[index]
                        sanitized_themes[name] = _sanitize_theme_values(values, fallback)

                for name, values in DEFAULT_THEME_DATA["themes"].items():  # type: ignore[assignment]
                        if name in sanitized_themes:
                                continue
                        if isinstance(values, Mapping):
                                sanitized_themes[name] = _sanitize_theme_values(values, values)

                merged["themes"] = sanitized_themes

                active_theme = raw_data.get("active_theme")
                if isinstance(active_theme, str) and active_theme in sanitized_themes:
                        merged["active_theme"] = active_theme
                else:
                        merged["active_theme"] = DEFAULT_THEME_NAME

                return merged

        def _save(self) -> None:
                with self.theme_file.open("w", encoding="utf-8") as handle:
                        json.dump(self._data, handle, ensure_ascii=False, indent=2)

        # ------------------------------------------------------------------
        # Public API
        # ------------------------------------------------------------------
        @property
        def themes(self) -> Dict[str, Dict[str, str]]:
                        return self._data["themes"]  # type: ignore[return-value]

        @property
        def active_theme_name(self) -> str:
                        return str(self._data.get("active_theme", DEFAULT_THEME_NAME))

        def theme_names(self) -> Iterable[str]:
                return self.themes.keys()

        def theme(self, name: str | None = None) -> Theme:
                theme_name = name or self.active_theme_name
                values = self.themes.get(theme_name)
                if values is None:
                        theme_name = DEFAULT_THEME_NAME
                        values = self.themes.get(theme_name, _sanitize_theme_values({}, DEFAULT_THEME_DATA["themes"][DEFAULT_THEME_NAME]))  # type: ignore[index]
                return Theme(theme_name, dict(values))

        def stylesheet(self, name: str | None = None) -> str:
                return self.theme(name).stylesheet()

        def set_active_theme(self, name: str) -> bool:
                if name not in self.themes:
                        return False
                if self.active_theme_name == name:
                        return True
                self._data["active_theme"] = name
                self._save()
                return True

