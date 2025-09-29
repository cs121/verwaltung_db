from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
	QComboBox,
	QDateEdit,
	QDialog,
	QDialogButtonBox,
	QGridLayout,
	QLabel,
	QLineEdit,
	QPlainTextEdit,
	QVBoxLayout,
	QWidget,
)

from inventar.data.models import Item
from inventar.utils.validators import DATE_FORMAT_QT_DISPLAY, ItemValidator


class ItemDialog(QDialog):
	"""Dialog zum Erstellen/Bearbeiten von Items."""

	def __init__(self, parent: QWidget | None = None, item: Optional[Item] = None, owners: Optional[list[str]] = None, object_types: Optional[list[str]] = None) -> None:
		super().__init__(parent)
		self.setWindowTitle('Neues Objekt einfügen' if item is None else 'Objekt bearbeiten')
		self.item = item
		self.owners = owners or []
		self.object_types = object_types or []
		self._build_ui()
		if item:
			self._populate(item)

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)

		form_layout = QGridLayout()
		self.objekttyp_combo = QComboBox()
		self.objekttyp_combo.setEditable(True)
		self.objekttyp_combo.setInsertPolicy(QComboBox.NoInsert)
		self.objekttyp_combo.addItem('')
		for objekttyp in sorted({value for value in self.object_types if value}):
			self.objekttyp_combo.addItem(objekttyp)
		self.hersteller_edit = QLineEdit()
		self.modell_edit = QLineEdit()
		self.seriennummer_edit = QLineEdit()

		self.einkaufsdatum_edit = QDateEdit()
		self.einkaufsdatum_edit.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
		self.einkaufsdatum_edit.setCalendarPopup(True)
		self.einkaufsdatum_edit.setSpecialValueText('')
		self.einkaufsdatum_edit.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
		self.einkaufsdatum_edit.setDate(QDate.currentDate())
		self.einkaufsdatum_edit.clear()
		self.zuweisungsdatum_edit = QDateEdit()
		self.zuweisungsdatum_edit.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
		self.zuweisungsdatum_edit.setCalendarPopup(True)
		self.zuweisungsdatum_edit.setSpecialValueText('')
		self.zuweisungsdatum_edit.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
		self.zuweisungsdatum_edit.setDate(QDate.currentDate())
		self.zuweisungsdatum_edit.clear()
		self.aktueller_besitzer_combo = QComboBox()
		self.aktueller_besitzer_combo.setEditable(True)
		self.aktueller_besitzer_combo.addItem('')
		for owner in sorted({value for value in self.owners if value}):
			self.aktueller_besitzer_combo.addItem(owner)
		self.anmerkungen_edit = QPlainTextEdit()

		form_layout.addWidget(QLabel('Objekttyp'), 0, 0)
		form_layout.addWidget(self.objekttyp_combo, 0, 1)
		form_layout.addWidget(QLabel('Hersteller'), 1, 0)
		form_layout.addWidget(self.hersteller_edit, 1, 1)
		form_layout.addWidget(QLabel('Modell'), 2, 0)
		form_layout.addWidget(self.modell_edit, 2, 1)

		form_layout.addWidget(QLabel('Seriennummer'), 0, 2)
		form_layout.addWidget(self.seriennummer_edit, 0, 3)
		form_layout.addWidget(QLabel('Einkaufsdatum'), 1, 2)
		form_layout.addWidget(self.einkaufsdatum_edit, 1, 3)
		form_layout.addWidget(QLabel('Zuweisungsdatum'), 2, 2)
		form_layout.addWidget(self.zuweisungsdatum_edit, 2, 3)
		form_layout.addWidget(QLabel('Aktueller Besitzer'), 3, 0)
		form_layout.addWidget(self.aktueller_besitzer_combo, 3, 1, 1, 3)

		layout.addLayout(form_layout)
		layout.addWidget(QLabel('Anmerkungen'))
		layout.addWidget(self.anmerkungen_edit)

		buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
		buttons.button(QDialogButtonBox.Save).setText('Speichern')
		buttons.button(QDialogButtonBox.Cancel).setText('Beenden')
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

		self.shortcut_save = QKeySequence(Qt.CTRL | Qt.Key_S)
		self.grabShortcut(self.shortcut_save)

	def _populate(self, item: Item) -> None:
		index = self.objekttyp_combo.findText(item.objekttyp)
		if index >= 0:
			self.objekttyp_combo.setCurrentIndex(index)
		else:
			self.objekttyp_combo.setEditText(item.objekttyp)
		self.hersteller_edit.setText(item.hersteller)
		self.modell_edit.setText(item.modell)
		self.seriennummer_edit.setText(item.seriennummer)
		if item.einkaufsdatum:
			qdate = QDate.fromString(item.einkaufsdatum, 'yyyy-MM-dd')
			if qdate.isValid():
				self.einkaufsdatum_edit.setDate(qdate)
		if item.zuweisungsdatum:
			assign_date = QDate.fromString(item.zuweisungsdatum, 'yyyy-MM-dd')
			if assign_date.isValid():
				self.zuweisungsdatum_edit.setDate(assign_date)
		index = self.aktueller_besitzer_combo.findText(item.aktueller_besitzer)
		if index >= 0:
			self.aktueller_besitzer_combo.setCurrentIndex(index)
		else:
			self.aktueller_besitzer_combo.setEditText(item.aktueller_besitzer)
		self.anmerkungen_edit.setPlainText(item.anmerkungen)

	def accept(self) -> None:  # type: ignore[override]
		valid, errors = ItemValidator.validate(self._collect_data(display_format=True))
		if not valid:
			self._show_errors(errors)
			return
		super().accept()

	def _collect_data(self, display_format: bool = False) -> dict:
		def _date_value(editor: QDateEdit) -> str:
			return editor.text() if display_format else (editor.date().toString('yyyy-MM-dd') if editor.text().strip() else '')

		return {
			'objekttyp': self.objekttyp_combo.currentText().strip(),
			'hersteller': self.hersteller_edit.text().strip(),
			'modell': self.modell_edit.text().strip(),
			'seriennummer': self.seriennummer_edit.text().strip(),
			'einkaufsdatum': _date_value(self.einkaufsdatum_edit),
			'zuweisungsdatum': _date_value(self.zuweisungsdatum_edit),
			'aktueller_besitzer': self.aktueller_besitzer_combo.currentText().strip(),
			'anmerkungen': self.anmerkungen_edit.toPlainText().strip(),
		}

	def _show_errors(self, errors: dict) -> None:
		messages = '\n'.join(f"{field}: {message}" for field, message in errors.items())
		from PySide6.QtWidgets import QMessageBox

		QMessageBox.warning(self, 'Eingabe ungültig', messages)

	def get_item_data(self) -> dict:
		return self._collect_data()

