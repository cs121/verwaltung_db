from __future__ import annotations

import locale
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QDate
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
	QAbstractItemView,
	QApplication,
	QComboBox,
	QDateEdit,
	QFileDialog,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QHeaderView,
	QInputDialog,
	QLabel,
	QLineEdit,
	QMainWindow,
	QMessageBox,
	QPushButton,
	QStatusBar,
	QTableView,
	QToolButton,
	QVBoxLayout,
	QWidget,
)

from inventar.data.models import Item
from inventar.data.repository import RepositoryError, create_repository
from inventar.export.exporters import export_to_csv, export_to_json, export_to_xlsx
from inventar.ui.item_dialog import ItemDialog
from inventar.ui.print import TablePrinter
from inventar.utils.settings import SettingsManager
from inventar.utils.validators import DATE_FORMAT_DISPLAY, ItemValidator


HEADERS = [
	"Nummer",
	"Objekttyp",
	"Hersteller",
	"Modell",
	"Seriennummer",
	"Einkaufsdatum",
	"Kaufpreis",
	"Aktueller Besitzer",
	"Anmerkungen",
]

COLUMN_KEYS = [
	"nummer",
	"objekttyp",
	"hersteller",
	"modell",
	"seriennummer",
	"einkaufsdatum",
	"kaufpreis",
	"aktueller_besitzer",
	"anmerkungen",
]

locale.setlocale(locale.LC_ALL, '')


def format_price(value: float) -> str:
	try:
		return locale.currency(value, grouping=True)
	except Exception:
		return f"{value:,.2f} €"


class ItemTableModel(QAbstractTableModel):
	"""TableModel für Inventaritems."""

	def __init__(self, items: Optional[List[Item]] = None) -> None:
		super().__init__()
		self._items: List[Item] = items or []

	def set_items(self, items: List[Item]) -> None:
		self.beginResetModel()
		self._items = list(items)
		self.endResetModel()

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
		return 0 if parent.isValid() else len(self._items)

	def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
		return 0 if parent.isValid() else len(COLUMN_KEYS)

	def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
		if not index.isValid():
			return None
		item = self._items[index.row()]
		key = COLUMN_KEYS[index.column()]
		value = getattr(item, key)
		if role == Qt.DisplayRole:
			if key == 'kaufpreis':
				return format_price(float(value or 0))
			if key == 'einkaufsdatum' and value:
				return datetime.strptime(value, '%Y-%m-%d').strftime(DATE_FORMAT_DISPLAY)
			return value
		if role == Qt.UserRole:
			return item
		return None

	def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # type: ignore[override]
		if role != Qt.DisplayRole:
			return None
		if orientation == Qt.Horizontal:
			return HEADERS[section]
		return section + 1

	def item_at(self, row: int) -> Optional[Item]:
		if 0 <= row < len(self._items):
			return self._items[row]
		return None


class MainWindow(QMainWindow):
	"""Hauptfenster der Inventarverwaltung."""

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle('Inventarliste Version 1.0')
		self.resize(1280, 720)

		self.settings = SettingsManager()
		self.repository, self.using_json_fallback = create_repository(Path.cwd())
		self.table_model = ItemTableModel()
		self.table = QTableView()
		self.table.setModel(self.table_model)
		self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SingleSelection)
		self.table.doubleClicked.connect(self.edit_selected_item)
		self.table.setSortingEnabled(True)
		self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

		self.printer = TablePrinter(self)

		self._font_size = 10
		self.items: List[Item] = []

		self._build_ui()
		self._create_actions()
		self._connect_signals()
		self._load_items()
		self.settings.restore_geometry(self)
		self._font_size = self.settings.restore_table(self.table)
		self._update_status()

		if self.using_json_fallback:
			self.statusBar().showMessage('JSON-Fallback aktiv – SQLite nicht verfügbar', 10000)

	def _build_ui(self) -> None:
		central = QWidget(self)
		layout = QVBoxLayout(central)

		layout.addWidget(self._build_search_box())
		layout.addLayout(self._build_form_filters())

		buttons_layout = QHBoxLayout()
		self.new_button = QPushButton('Neues Objekt')
		self.edit_button = QPushButton('Bearbeiten')
		self.delete_button = QPushButton('Löschen')
		self.reset_button = QPushButton('Reset')
		self.export_excel_button = QPushButton('Excel')
		self.export_csv_button = QPushButton('CSV')
		self.export_json_button = QPushButton('JSON')
		self.print_button = QPushButton()
		self.print_button.setIcon(QIcon.fromTheme('document-print'))
		self.print_button.setToolTip('Drucken (Ctrl+P)')

		buttons_layout.addWidget(self.new_button)
		buttons_layout.addWidget(self.edit_button)
		buttons_layout.addWidget(self.delete_button)
		buttons_layout.addWidget(self.reset_button)
		buttons_layout.addStretch()
		buttons_layout.addWidget(self.export_excel_button)
		buttons_layout.addWidget(self.export_csv_button)
		buttons_layout.addWidget(self.export_json_button)
		buttons_layout.addWidget(self.print_button)

		layout.addLayout(buttons_layout)
		layout.addWidget(self.table)

		zoom_layout = QHBoxLayout()
		zoom_layout.addStretch()
		self.zoom_out_button = QToolButton()
		self.zoom_out_button.setText('−')
		self.zoom_in_button = QToolButton()
		self.zoom_in_button.setText('+')
		zoom_layout.addWidget(QLabel('Zoom'))
		zoom_layout.addWidget(self.zoom_out_button)
		zoom_layout.addWidget(self.zoom_in_button)
		layout.addLayout(zoom_layout)

		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)

		self.setCentralWidget(central)

	def _build_search_box(self) -> QWidget:
		box = QGroupBox('Suchen')
		layout = QHBoxLayout(box)
		self.search_criteria = QComboBox()
		self.search_criteria.addItems([
			'Nummer',
			'Seriennummer',
			'Objekttyp',
			'Hersteller',
			'Modell',
			'Aktueller Besitzer',
		])
		self.search_field = QLineEdit()
		self.search_field.setPlaceholderText('Suchbegriff eingeben ...')
		self.search_button = QPushButton()
		self.search_button.setIcon(QIcon.fromTheme('system-search'))
		self.search_button.setText('Suchen')

		layout.addWidget(QLabel('Kriterium'))
		layout.addWidget(self.search_criteria)
		layout.addWidget(self.search_field)
		layout.addWidget(self.search_button)
		return box

	def _build_form_filters(self) -> QHBoxLayout:
		layout = QHBoxLayout()

		left_layout = QFormLayout()
		self.filter_nummer = QLineEdit()
		self.filter_objekttyp = QLineEdit()
		self.filter_hersteller = QLineEdit()
		self.filter_modell = QLineEdit()
		left_layout.addRow('Nummer', self.filter_nummer)
		left_layout.addRow('Objekttyp', self.filter_objekttyp)
		left_layout.addRow('Hersteller', self.filter_hersteller)
		left_layout.addRow('Modell', self.filter_modell)

		right_layout = QFormLayout()
		self.filter_seriennummer = QLineEdit()
		self.filter_einkaufsdatum = QDateEdit()
		self.filter_einkaufsdatum.setDisplayFormat(DATE_FORMAT_DISPLAY)
		self.filter_einkaufsdatum.setCalendarPopup(True)
		self.filter_einkaufsdatum.setSpecialValueText('')
		self.filter_einkaufsdatum.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
		self.filter_einkaufsdatum.setDate(QDate.currentDate())
		self.filter_einkaufsdatum.clear()
		self.filter_kaufpreis = QLineEdit()
		self.filter_besitzer = QComboBox()
		self.filter_besitzer.setEditable(True)
		self.filter_besitzer.setInsertPolicy(QComboBox.NoInsert)
		self.filter_anmerkungen = QLineEdit()
		self.add_owner_button = QToolButton()
		self.add_owner_button.setText('+')
		owner_layout = QHBoxLayout()
		owner_layout.addWidget(self.filter_besitzer)
		owner_layout.addWidget(self.add_owner_button)
		owner_layout.setContentsMargins(0, 0, 0, 0)
		owner_layout.setSpacing(4)
		right_layout.addRow('Seriennummer', self.filter_seriennummer)
		right_layout.addRow('Einkaufsdatum', self.filter_einkaufsdatum)
		right_layout.addRow('Kaufpreis', self.filter_kaufpreis)
		right_layout.addRow('Aktueller Besitzer', owner_layout)
		right_layout.addRow('Anmerkungen', self.filter_anmerkungen)

		layout.addLayout(left_layout)
		layout.addLayout(right_layout)
		return layout

	def _create_actions(self) -> None:
		self.new_action = QAction('Neu', self)
		self.new_action.setShortcut(QKeySequence.New)
		self.edit_action = QAction('Bearbeiten', self)
		self.edit_action.setShortcut(QKeySequence('Ctrl+E'))
		self.delete_action = QAction('Löschen', self)
		self.delete_action.setShortcut(QKeySequence.Delete)
		self.search_action = QAction('Suche', self)
		self.search_action.setShortcut(QKeySequence.Find)
		self.print_action = QAction('Drucken', self)
		self.print_action.setShortcut(QKeySequence.Print)

		for action in [self.new_action, self.edit_action, self.delete_action, self.search_action, self.print_action]:
			self.addAction(action)

	def _connect_signals(self) -> None:
		self.new_button.clicked.connect(self.create_item)
		self.edit_button.clicked.connect(self.edit_selected_item)
		self.delete_button.clicked.connect(self.delete_selected_item)
		self.reset_button.clicked.connect(self.reset_filters)
		self.export_excel_button.clicked.connect(partial(self.export_data, 'xlsx'))
		self.export_csv_button.clicked.connect(partial(self.export_data, 'csv'))
		self.export_json_button.clicked.connect(partial(self.export_data, 'json'))
		self.print_button.clicked.connect(self.print_preview)

		self.zoom_in_button.clicked.connect(lambda: self._adjust_font_size(1))
		self.zoom_out_button.clicked.connect(lambda: self._adjust_font_size(-1))

		self.search_button.clicked.connect(self.apply_filters)
		self.search_field.returnPressed.connect(self.apply_filters)

		self.new_action.triggered.connect(self.create_item)
		self.edit_action.triggered.connect(self.edit_selected_item)
		self.delete_action.triggered.connect(self.delete_selected_item)
		self.search_action.triggered.connect(lambda: self.search_field.setFocus())
		self.print_action.triggered.connect(self.print_preview)

		self.filter_nummer.returnPressed.connect(self.apply_filters)
		self.filter_objekttyp.returnPressed.connect(self.apply_filters)
		self.filter_hersteller.returnPressed.connect(self.apply_filters)
		self.filter_modell.returnPressed.connect(self.apply_filters)
		self.filter_seriennummer.returnPressed.connect(self.apply_filters)
		self.filter_kaufpreis.returnPressed.connect(self.apply_filters)
		self.filter_anmerkungen.returnPressed.connect(self.apply_filters)
		if self.filter_besitzer.lineEdit():
			self.filter_besitzer.lineEdit().returnPressed.connect(self.apply_filters)
		self.add_owner_button.clicked.connect(self._add_owner_filter_value)

	def _load_items(self) -> None:
		self.items = self.repository.list()
		self.table_model.set_items(self.items)
		self._update_owner_combo()
		self._update_status()

	def _update_owner_combo(self) -> None:
		owners = self.repository.distinct_owners()
		current_text = self.filter_besitzer.currentText()
		self.filter_besitzer.blockSignals(True)
		self.filter_besitzer.clear()
		self.filter_besitzer.addItem('')
		self.filter_besitzer.addItems(owners)
		self.filter_besitzer.setCurrentText(current_text)
		self.filter_besitzer.blockSignals(False)

	def _add_owner_filter_value(self) -> None:
		text, ok = QInputDialog.getText(self, 'Besitzer hinzufügen', 'Neuen Besitzer eingeben:')
		if not ok:
			return
		value = text.strip()
		if not value:
			return
		if self.filter_besitzer.findText(value) == -1:
			self.filter_besitzer.addItem(value)
		self.filter_besitzer.setCurrentText(value)

	def _update_status(self) -> None:
		total = len(self.table_model._items)
		self.statusBar().showMessage(f'Gesamtobjekte: {total}')

	def reset_filters(self) -> None:
		self.search_field.clear()
		self.filter_nummer.clear()
		self.filter_objekttyp.clear()
		self.filter_hersteller.clear()
		self.filter_modell.clear()
		self.filter_seriennummer.clear()
		self.filter_kaufpreis.clear()
		self.filter_anmerkungen.clear()
		self.filter_besitzer.setCurrentIndex(0)
		self.filter_einkaufsdatum.clear()
		self._load_items()

	def apply_filters(self) -> None:
		filters: dict[str, str] = {}
		criteria_key = {
			'Nummer': 'nummer',
			'Seriennummer': 'seriennummer',
			'Objekttyp': 'objekttyp',
			'Hersteller': 'hersteller',
			'Modell': 'modell',
			'Aktueller Besitzer': 'aktueller_besitzer',
		}
		selected_key = criteria_key.get(self.search_criteria.currentText(), 'nummer')
		search_text = self.search_field.text().strip()
		if search_text:
			filters[selected_key] = search_text

		for widget, key in [
			(self.filter_nummer, 'nummer'),
			(self.filter_objekttyp, 'objekttyp'),
			(self.filter_hersteller, 'hersteller'),
			(self.filter_modell, 'modell'),
			(self.filter_seriennummer, 'seriennummer'),
			(self.filter_anmerkungen, 'anmerkungen'),
		]:
			value = widget.text().strip()
			if value:
				filters[key] = value

		besitzer = self.filter_besitzer.currentText().strip()
		if besitzer:
			filters['aktueller_besitzer'] = besitzer

		preis = self.filter_kaufpreis.text().strip()
		if preis:
			filters['kaufpreis'] = preis.replace(',', '.').strip()

		datums_text = self.filter_einkaufsdatum.text().strip()
		if datums_text:
			filters['einkaufsdatum'] = ItemValidator.convert_display_to_iso(datums_text)

		self.items = self.repository.list(filters if filters else None)
		self.table_model.set_items(self.items)
		self._update_status()
		self.statusBar().showMessage(f'{len(self.items)} Einträge gefiltert', 5000)

	def _collect_dialog_data(self, dialog: ItemDialog) -> Item:
		data = dialog.get_item_data()
		return Item(
			nummer=data['nummer'],
			objekttyp=data['objekttyp'],
			hersteller=data['hersteller'],
			modell=data['modell'],
			seriennummer=data['seriennummer'],
			einkaufsdatum=data['einkaufsdatum'],
			kaufpreis=float(data['kaufpreis'] or 0),
			aktueller_besitzer=data['aktueller_besitzer'],
			anmerkungen=data['anmerkungen'],
		)

	def create_item(self) -> None:
		dialog = ItemDialog(self, owners=self.repository.distinct_owners())
		if dialog.exec() == ItemDialog.Accepted:
			item = self._collect_dialog_data(dialog)
			try:
				created = self.repository.create(item)
			except RepositoryError as exc:
				QMessageBox.critical(self, 'Fehler', str(exc))
				return
			self._load_items()
			self._select_item(created)
			self.statusBar().showMessage('Objekt angelegt', 4000)

	def edit_selected_item(self) -> None:
		selected = self._current_item()
		if not selected:
			return
		dialog = ItemDialog(self, item=selected, owners=self.repository.distinct_owners())
		if dialog.exec() != ItemDialog.Accepted:
			return
		item_data = self._collect_dialog_data(dialog)
		try:
			updated = self.repository.update(selected.id, item_data)  # type: ignore[arg-type]
		except RepositoryError as exc:
			QMessageBox.critical(self, 'Fehler', str(exc))
			return
		self._load_items()
		self._select_item(updated)
		self.statusBar().showMessage('Objekt aktualisiert', 4000)

	def delete_selected_item(self) -> None:
		selected = self._current_item()
		if not selected:
			return
		if QMessageBox.question(self, 'Löschen bestätigen', 'Soll das ausgewählte Objekt gelöscht werden?') != QMessageBox.Yes:
			return
		try:
			self.repository.delete(selected.id)  # type: ignore[arg-type]
		except RepositoryError as exc:
			QMessageBox.critical(self, 'Fehler', str(exc))
			return
		self._load_items()
		self.statusBar().showMessage('Objekt gelöscht', 4000)

	def _current_item(self) -> Optional[Item]:
		selection = self.table.selectionModel()
		if not selection:
			return None
		indexes = selection.selectedRows()
		if not indexes:
			return None
		row = indexes[0].row()
		return self.table_model.item_at(row)

	def _select_item(self, item: Item) -> None:
		for row, existing in enumerate(self.table_model._items):
			if existing.id == item.id:
				index = self.table_model.index(row, 0)
				self.table.selectRow(index.row())
				self.table.scrollTo(index)
				break

	def closeEvent(self, event) -> None:  # type: ignore[override]
		self.settings.save_geometry(self)
		self.settings.save_table(self.table, self._font_size)
		super().closeEvent(event)

	def export_data(self, export_type: str) -> None:
		items = self.table_model._items
		if not items:
			QMessageBox.information(self, 'Export', 'Keine Daten zum Exportieren vorhanden.')
			return
		dialog_title = 'Datei speichern'
		suffix = {
			'xlsx': 'Excel-Dateien (*.xlsx)',
			'csv': 'CSV-Dateien (*.csv)',
			'json': 'JSON-Dateien (*.json)',
		}[export_type]
		path, _ = QFileDialog.getSaveFileName(self, dialog_title, '', suffix)
		if not path:
			return
		exporters = {
			'xlsx': export_to_xlsx,
			'csv': export_to_csv,
			'json': export_to_json,
		}
		exporters[export_type](items, Path(path))
		self.statusBar().showMessage(f'Export erfolgreich: {path}', 4000)

	def print_preview(self) -> None:
		self.printer.preview(self.table_model._items, len(self.table_model._items))

	def _adjust_font_size(self, delta: int) -> None:
		self._font_size = max(8, min(24, self._font_size + delta))
		self.settings.apply_table_font(self.table, self._font_size)
		self.statusBar().showMessage(f'Schriftgröße: {self._font_size}', 2000)


def run() -> None:
	app = QApplication.instance() or QApplication([])
	window = MainWindow()
	window.show()
	app.exec()
