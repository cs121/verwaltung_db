from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QTableView

ORGANIZATION = 'Inventarverwaltung'
APPLICATION = 'Inventarliste'


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

	@staticmethod
	def apply_table_font(table: QTableView, font_size: int) -> None:
		font = table.font()
		font.setPointSize(font_size)
		table.setFont(font)
		table.verticalHeader().setDefaultSectionSize(font_size + 14)
		table.horizontalHeader().setMinimumSectionSize(50)

	def clear(self) -> None:
		self.settings.clear()
