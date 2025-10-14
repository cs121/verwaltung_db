from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QTableView

ORGANIZATION = 'Inventarverwaltung'
APPLICATION = 'Inventarliste'
OBJECT_TYPES_KEY = 'object_types/custom'
DEFAULT_OBJECT_TYPES = ['Notebook', 'PC', 'Tablet', 'Mobiltelefon', 'Drucker']
DATABASE_PATH_KEY = 'storage/database_path'


class SettingsManager:
        """Verwaltet QSettings für Fenster und Tabelle."""

        def __init__(self) -> None:
                self.settings = QSettings(ORGANIZATION, APPLICATION)

        def restore_geometry(self, widget) -> None:
                geometry = self.settings.value('main_window/geometry')
                if geometry is not None:
                        widget.restoreGeometry(geometry)

        def save_geometry(self, widget) -> None:
                self.settings.setValue('main_window/geometry', widget.saveGeometry())

        def restore_table(self, table: QTableView) -> int:
                header_state = self.settings.value('table/state')
                if header_state is not None:
                        table.horizontalHeader().restoreState(header_state)
                font_size = int(self.settings.value('table/font_size', 10))
                self.apply_table_font(table, font_size)
                return font_size

        def save_table(self, table: QTableView, font_size: int) -> None:
                self.settings.setValue('table/state', table.horizontalHeader().saveState())
                self.settings.setValue('table/font_size', font_size)

        def load_database_path(self, default: Path) -> Path:
                value = self.settings.value(DATABASE_PATH_KEY, str(default))
                if isinstance(value, Path):
                        return value
                if isinstance(value, str):
                        text = value.strip()
                        return Path(text) if text else default
                if value is None:
                        return default
                text = str(value).strip()
                return Path(text) if text else default

        def save_database_path(self, path: Path) -> None:
                self.settings.setValue(DATABASE_PATH_KEY, str(Path(path)))

        @staticmethod
        def apply_table_font(table: QTableView, font_size: int) -> None:
                font = table.font()
                font.setPointSize(font_size)
                table.setFont(font)
                table.verticalHeader().setDefaultSectionSize(font_size + 14)
                table.horizontalHeader().setMinimumSectionSize(50)

        def clear(self) -> None:
                self.settings.clear()

        @staticmethod
        def _normalize_object_types(values: Iterable[str]) -> list[str]:
                result: list[str] = []
                seen: set[str] = set()
                for value in values:
                        text = str(value).strip()
                        if not text:
                                continue
                        key = text.lower()
                        if key in seen:
                                continue
                        seen.add(key)
                        result.append(text)
                return result

        def load_object_types(self) -> list[str]:
                stored = self.settings.value(OBJECT_TYPES_KEY, [])
                if isinstance(stored, str):
                        stored_values = [stored]
                elif isinstance(stored, list):
                        stored_values = [str(value) for value in stored]
                else:
                        stored_values = []
                return self._normalize_object_types(DEFAULT_OBJECT_TYPES + stored_values)

        def save_object_types(self, object_types: Iterable[str]) -> list[str]:
                normalized = self._normalize_object_types(object_types)
                default_lower = {value.lower() for value in DEFAULT_OBJECT_TYPES}
                custom = [value for value in normalized if value.lower() not in default_lower]
                self.settings.setValue(OBJECT_TYPES_KEY, custom)
                return normalized

        def add_object_type(self, object_type: str) -> list[str]:
                types = self.load_object_types()
                types.append(object_type)
                return self.save_object_types(types)

        def sync_object_types(self, object_types: Iterable[str]) -> list[str]:
                types = self.load_object_types()
                types.extend(object_types)
                return self.save_object_types(types)
