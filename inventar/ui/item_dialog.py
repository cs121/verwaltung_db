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
from inventar.utils.validators import DATE_FORMAT_DISPLAY, ItemValidator


class ItemDialog(QDialog):
	"""Dialog zum Erstellen/Bearbeiten von Items."""

	def __init__(self, parent: QWidget | None = None, item: Optional[Item] = None, owners: Optional[list[str]] = None) -> None:
		super().__init__(parent)
		self.setWindowTitle('Neues Objekt einfügen' if item is None else 'Objekt bearbeiten')
		self.item = item
		self.owners = owners or []
		self._build_ui()
		if item:
			self._populate(item)

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)

		form_layout = QGridLayout()
		self.nummer_edit = QLineEdit()
		self.objekttyp_edit = QLineEdit()
		self.hersteller_edit = QLineEdit()
		self.modell_edit = QLineEdit()

		self.seriennummer_edit = QLineEdit()
		self.einkaufsdatum_edit = QDateEdit()
		self.einkaufsdatum_edit.setDisplayFormat(DATE_FORMAT_DISPLAY)
		self.einkaufsdatum_edit.setCalendarPopup(True)
		self.kaufpreis_edit = QLineEdit()
		self.aktueller_besitzer_combo = QComboBox()
		self.aktueller_besitzer_combo.setEditable(True)
		self.aktueller_besitzer_combo.addItems(sorted(self.owners))
		self.anmerkungen_edit = QPlainTextEdit()

		form_layout.addWidget(QLabel('Nummer'), 0, 0)
		form_layout.addWidget(self.nummer_edit, 0, 1)
		form_layout.addWidget(QLabel('Objekttyp'), 1, 0)
		form_layout.addWidget(self.objekttyp_edit, 1, 1)
		form_layout.addWidget(QLabel('Hersteller'), 2, 0)
		form_layout.addWidget(self.hersteller_edit, 2, 1)
		form_layout.addWidget(QLabel('Modell'), 3, 0)
		form_layout.addWidget(self.modell_edit, 3, 1)

		form_layout.addWidget(QLabel('Seriennummer'), 0, 2)
		form_layout.addWidget(self.seriennummer_edit, 0, 3)
		form_layout.addWidget(QLabel('Einkaufsdatum'), 1, 2)
		form_layout.addWidget(self.einkaufsdatum_edit, 1, 3)
		form_layout.addWidget(QLabel('Kaufpreis'), 2, 2)
		form_layout.addWidget(self.kaufpreis_edit, 2, 3)
		form_layout.addWidget(QLabel('Aktueller Besitzer'), 3, 2)
		form_layout.addWidget(self.aktueller_besitzer_combo, 3, 3)

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
		self.nummer_edit.setText(item.nummer)
		self.objekttyp_edit.setText(item.objekttyp)
		self.hersteller_edit.setText(item.hersteller)
		self.modell_edit.setText(item.modell)
		self.seriennummer_edit.setText(item.seriennummer)
		if item.einkaufsdatum:
			qdate = QDate.fromString(item.einkaufsdatum, 'yyyy-MM-dd')
			if qdate.isValid():
				self.einkaufsdatum_edit.setDate(qdate)
		self.kaufpreis_edit.setText(str(item.kaufpreis))
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
		return {
			'nummer': self.nummer_edit.text().strip(),
			'objekttyp': self.objekttyp_edit.text().strip(),
			'hersteller': self.hersteller_edit.text().strip(),
			'modell': self.modell_edit.text().strip(),
			'seriennummer': self.seriennummer_edit.text().strip(),
			'einkaufsdatum': self.einkaufsdatum_edit.text() if display_format else self.einkaufsdatum_edit.date().toString('yyyy-MM-dd'),
			'kaufpreis': self.kaufpreis_edit.text().replace(',', '.'),
			'aktueller_besitzer': self.aktueller_besitzer_combo.currentText().strip(),
			'anmerkungen': self.anmerkungen_edit.toPlainText().strip(),
		}

	def _show_errors(self, errors: dict) -> None:
		messages = '\n'.join(f"{field}: {message}" for field, message in errors.items())
		from PySide6.QtWidgets import QMessageBox

		QMessageBox.warning(self, 'Eingabe ungültig', messages)

	def get_item_data(self) -> dict:
		return self._collect_data()
