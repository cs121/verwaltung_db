from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QDate, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QColor, QFont
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
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
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
from inventar.utils.validators import DATE_FORMAT_DISPLAY, DATE_FORMAT_QT_DISPLAY, ItemValidator


PALETTE_STYLESHEET = """
QMainWindow {
        background-color: #c4ebf2;
        color: #2C2C2C;
}

QWidget {
        background-color: #c4ebf2;
        color: #2C2C2C;
}

QLabel,
QStatusBar QLabel {
        color: #2C2C2C;
}

QGroupBox {
        background-color: #add9e6;
        border: 1px solid #88c7e6;
        border-radius: 8px;
        margin-top: 12px;
        padding: 12px;
}

QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 4px;
        color: #88c7e6;
}

QPushButton,
QToolButton {
        background-color: #ffd302;
        color: #2C2C2C;
        border: none;
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 600;
}

QPushButton:hover,
QToolButton:hover {
        background-color: #fff683;
}

QPushButton:pressed,
QToolButton:pressed {
        background-color: #ffffc1;
}

QPushButton:disabled,
QToolButton:disabled {
        background-color: #add9e6;
        color: #6F6F6F;
}

QLineEdit,
QComboBox,
QDateEdit {
        background-color: #FFFFFF;
        border: 1px solid #88c7e6;
        border-radius: 4px;
        padding: 4px 6px;
}

QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus {
        border: 1px solid #ffd302;
}

QComboBox QAbstractItemView,
QDateEdit QAbstractItemView {
        background-color: #FFFFFF;
        border: 1px solid #88c7e6;
        selection-background-color: #ffd302;
        selection-color: #2C2C2C;
}

QTableView {
        background-color: #FFFFFF;
        alternate-background-color: #add9e6;
        gridline-color: #add9e6;
        border: 1px solid #88c7e6;
        selection-background-color: #ffd302;
        selection-color: #2C2C2C;
}

QTableView::item:selected {
        background-color: #ffd302;
        color: #2C2C2C;
}

QHeaderView::section {
        background-color: #88c7e6;
        color: #2C2C2C;
        padding: 8px;
        border: none;
        border-right: 1px solid #c4ebf2;
}

QTableCornerButton::section {
        background-color: #88c7e6;
        border: none;
}

QStatusBar {
        background-color: #ffd302;
        color: #2C2C2C;
        border-top: 1px solid #add9e6;
}

QStatusBar QLabel {
        color: #2C2C2C;
}

QScrollBar:vertical,
QScrollBar:horizontal {
        background: #add9e6;
        border: none;
        border-radius: 4px;
        margin: 0px;
}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
        background: #ffd302;
        border-radius: 4px;
        min-height: 20px;
        min-width: 20px;
}

QScrollBar::add-line,
QScrollBar::sub-line {
        background: none;
}
"""


HEADERS = [
        "Objekttyp",
        "Hersteller",
        "Modell",
        "Seriennummer",
        "Einkaufsdatum",
        "Zuweisungsdatum",
        "Aktueller Besitzer",
        "Anmerkungen",
]

COLUMN_KEYS = [
        "objekttyp",
        "hersteller",
        "modell",
        "seriennummer",
        "einkaufsdatum",
        "zuweisungsdatum",
        "aktueller_besitzer",
        "anmerkungen",
]

CUSTOM_CATEGORY_MANUFACTURER = "manufacturer"
CUSTOM_CATEGORY_MODEL = "model"
CUSTOM_CATEGORY_SERIAL = "serial_number"
CUSTOM_CATEGORY_OWNER = "owner"


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
                        if key in {'einkaufsdatum', 'zuweisungsdatum'} and value:
                                return datetime.strptime(value, '%Y-%m-%d').strftime(DATE_FORMAT_DISPLAY)
                        return value
                if role == Qt.UserRole:
                        return item
                if role == Qt.ForegroundRole and getattr(item, 'stillgelegt', False):
                        return QColor(Qt.red)
                if role == Qt.BackgroundRole and getattr(item, 'stillgelegt', False):
                        return QColor(255, 205, 210)
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
                self.object_types: List[str] = self.settings.load_object_types()
                self.custom_manufacturers: list[str] = self.repository.list_custom_values(
                        CUSTOM_CATEGORY_MANUFACTURER
                )
                self.custom_models: list[str] = self.repository.list_custom_values(CUSTOM_CATEGORY_MODEL)
                self.custom_serial_numbers: list[str] = self.repository.list_custom_values(CUSTOM_CATEGORY_SERIAL)
                self.custom_owners: list[str] = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                self.table_model = ItemTableModel()
                self.table = QTableView()
                self.table.setModel(self.table_model)
                self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
                self.table.setSelectionMode(QAbstractItemView.SingleSelection)
                self.table.doubleClicked.connect(self.edit_selected_item)
                self.table.setSortingEnabled(True)

                # RESPONSIVE DESIGN: Tabelle passt sich der Breite an
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.table.horizontalHeader().setStretchLastSection(True)

                self.table.setAlternatingRowColors(True)
                self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

                self.printer = TablePrinter(self)

                self._font_size = 10
                self.items: List[Item] = []
                self.filtered_items: List[Item] = []

                self._filter_timer = QTimer(self)
                self._filter_timer.setSingleShot(True)
                self._filter_timer.setInterval(250)
                self._filter_timer.timeout.connect(self.apply_filters)

                self._build_ui()
                self._apply_color_palette()
                self._create_actions()
                self._connect_signals()
                self._load_items()
                self.settings.restore_geometry(self)
                try:
                        self._font_size = self.settings.restore_table(self.table)
                except Exception:
                        pass
                self._update_status()

                if self.using_json_fallback:
                        self.statusBar().showMessage('JSON-Fallback aktiv – SQLite nicht verfügbar', 10000)

        # ---------- UI Aufbau ----------
        def _build_ui(self) -> None:
                central = QWidget(self)
                central.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                layout = QVBoxLayout(central)
                layout.setContentsMargins(10, 10, 10, 10)

                layout.addWidget(self._build_search_box())
                layout.addWidget(self._build_form_filters())

                actions_layout = QHBoxLayout()
                self.new_button = QPushButton('Neues Objekt')
                self.export_button = QToolButton()
                self.export_button.setText('Export')
                self.export_button.setPopupMode(QToolButton.InstantPopup)
                self.export_menu = QMenu(self.export_button)
                self.export_button.setMenu(self.export_menu)
                self.export_excel_action = self.export_menu.addAction('Excel')
                self.export_csv_action = self.export_menu.addAction('CSV')
                self.export_json_action = self.export_menu.addAction('JSON')
                self.print_button = QPushButton()
                self.print_button.setIcon(QIcon.fromTheme('document-print'))
                self.print_button.setToolTip('Drucken (Ctrl+P)')

                actions_layout.addWidget(self.new_button)
                actions_layout.addStretch()

                layout.addLayout(actions_layout)

                # RESPONSIVE: Tabelle mit maximaler Ausdehnung
                layout.addWidget(self.table, stretch=1)

                bottom_layout = QHBoxLayout()
                bottom_layout.addWidget(self.export_button)
                bottom_layout.addWidget(self.print_button)
                bottom_layout.addStretch()
                layout.addLayout(bottom_layout)

                self.status_bar = QStatusBar()
                self.setStatusBar(self.status_bar)

                self.setCentralWidget(central)

        def _apply_color_palette(self) -> None:
                """Apply the corporate color palette to the main window widgets."""
                self.setStyleSheet(PALETTE_STYLESHEET)

        def _build_search_box(self) -> QWidget:
                box = QGroupBox('Suchen')
                box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                box.setStyleSheet('QGroupBox::title { color: black; font-weight: bold; }')
                layout = QHBoxLayout(box)
                self.search_field = QLineEdit()
                self.search_field.setPlaceholderText('In allen Feldern suchen ...')
                self.search_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                layout.addWidget(self.search_field)
                return box

        def _build_form_filters(self) -> QWidget:
                box = QGroupBox('Filter')
                box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                box.setStyleSheet('QGroupBox::title { color: black; font-weight: bold; }')
                layout = QHBoxLayout(box)

                left_layout = QFormLayout()
                self.filter_objekttyp = QComboBox()
                self.filter_objekttyp.setEditable(True)
                self.filter_objekttyp.setInsertPolicy(QComboBox.NoInsert)
                self.filter_objekttyp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_object_type_filter()

                self.filter_hersteller = QComboBox()
                self.filter_hersteller.setEditable(True)
                self.filter_hersteller.setInsertPolicy(QComboBox.NoInsert)
                self.filter_hersteller.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_manufacturer_filter()

                self.filter_modell = QComboBox()
                self.filter_modell.setEditable(True)
                self.filter_modell.setInsertPolicy(QComboBox.NoInsert)
                self.filter_modell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_model_filter()

                self.filter_seriennummer = QComboBox()
                self.filter_seriennummer.setEditable(True)
                self.filter_seriennummer.setInsertPolicy(QComboBox.NoInsert)
                self.filter_seriennummer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_serial_filter()

                left_layout.addRow('Objekttyp', self.filter_objekttyp)
                left_layout.addRow('Hersteller', self.filter_hersteller)
                left_layout.addRow('Modell', self.filter_modell)
                left_layout.addRow('Seriennummer', self.filter_seriennummer)

                right_layout = QFormLayout()
                self.filter_einkaufsdatum = QDateEdit()
                self.filter_einkaufsdatum.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
                self.filter_einkaufsdatum.setCalendarPopup(True)
                self.filter_einkaufsdatum.setSpecialValueText('')
                self.filter_einkaufsdatum.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
                self.filter_einkaufsdatum.setDate(QDate.currentDate())
                self.filter_einkaufsdatum.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                if self.filter_einkaufsdatum.lineEdit():
                        self.filter_einkaufsdatum.lineEdit().setText('')
                self.filter_zuweisungsdatum = QDateEdit()
                self.filter_zuweisungsdatum.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
                self.filter_zuweisungsdatum.setCalendarPopup(True)
                self.filter_zuweisungsdatum.setSpecialValueText('')
                self.filter_zuweisungsdatum.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
                self.filter_zuweisungsdatum.setDate(QDate.currentDate())
                self.filter_zuweisungsdatum.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                if self.filter_zuweisungsdatum.lineEdit():
                        self.filter_zuweisungsdatum.lineEdit().setText('')
                self.filter_besitzer = QComboBox()
                self.filter_besitzer.setEditable(True)
                self.filter_besitzer.setInsertPolicy(QComboBox.NoInsert)
                self.filter_besitzer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_owner_combo()
                self.filter_anmerkungen = QLineEdit()
                self.filter_anmerkungen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.add_owner_button = QToolButton()
                self.add_owner_button.setText('+')
                self.add_owner_button.setToolTip('Besitzer zur Auswahlliste hinzufügen')
                self.remove_owner_button = QToolButton()
                self.remove_owner_button.setText('−')
                self.remove_owner_button.setToolTip('Ausgewählten Besitzer aus allen Einträgen entfernen')
                owner_layout = QHBoxLayout()
                owner_layout.addWidget(self.filter_besitzer)
                owner_layout.addWidget(self.add_owner_button)
                owner_layout.addWidget(self.remove_owner_button)
                owner_layout.setContentsMargins(0, 0, 0, 0)
                owner_layout.setSpacing(4)
                right_layout.addRow('Einkaufsdatum', self.filter_einkaufsdatum)
                right_layout.addRow('Zuweisungsdatum', self.filter_zuweisungsdatum)
                owner_layout.setStretch(0, 1)
                right_layout.addRow('Aktueller Besitzer', owner_layout)
                right_layout.addRow('Anmerkungen', self.filter_anmerkungen)

                combo_boxes = [
                        self.filter_objekttyp,
                        self.filter_hersteller,
                        self.filter_modell,
                        self.filter_seriennummer,
                        self.filter_besitzer,
                ]

                max_width = max(combo.sizeHint().width() for combo in combo_boxes)
                for combo in combo_boxes:
                        combo.setMinimumWidth(max_width)
                        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                layout.addLayout(left_layout)
                layout.addLayout(right_layout)

                self._style_form_labels(left_layout)
                self._style_form_labels(right_layout)

                return box

        @staticmethod
        def _style_form_labels(layout: QFormLayout) -> None:
                """Apply the required style to the labels in a form layout."""
                for row in range(layout.rowCount()):
                        item = layout.itemAt(row, QFormLayout.LabelRole)
                        if not item:
                                continue
                        label = item.widget()
                        if label is None:
                                continue
                        label.setStyleSheet('color: black; font-weight: bold;')

        # ---------- Aktionen & Signale ----------
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
                self.export_excel_action.triggered.connect(lambda: self.export_data('xlsx'))
                self.export_csv_action.triggered.connect(lambda: self.export_data('csv'))
                self.export_json_action.triggered.connect(lambda: self.export_data('json'))
                self.print_button.clicked.connect(self.print_preview)

                self.search_field.returnPressed.connect(self._handle_search_submit)
                self.search_field.textChanged.connect(self._handle_search_text_change)

                self.remove_owner_button.clicked.connect(self._remove_owner_filter_value)
                self.new_action.triggered.connect(self.create_item)
                self.edit_action.triggered.connect(self.edit_selected_item)
                self.delete_action.triggered.connect(self.delete_selected_item)
                self.search_action.triggered.connect(lambda: self.search_field.setFocus())
                self.print_action.triggered.connect(self.print_preview)

                if self.filter_hersteller.lineEdit():
                        self.filter_hersteller.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_hersteller.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_hersteller.currentIndexChanged.connect(self._schedule_filter_update)
                if self.filter_modell.lineEdit():
                        self.filter_modell.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_modell.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_modell.currentIndexChanged.connect(self._schedule_filter_update)
                if self.filter_seriennummer.lineEdit():
                        self.filter_seriennummer.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_seriennummer.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_seriennummer.currentIndexChanged.connect(self._schedule_filter_update)
                self.filter_anmerkungen.returnPressed.connect(self.apply_filters)
                self.filter_anmerkungen.textChanged.connect(self._schedule_filter_update)
                if self.filter_objekttyp.lineEdit():
                        self.filter_objekttyp.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_objekttyp.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_objekttyp.currentIndexChanged.connect(self._schedule_filter_update)
                if self.filter_besitzer.lineEdit():
                        self.filter_besitzer.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_besitzer.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_besitzer.currentIndexChanged.connect(self._schedule_filter_update)
                self.filter_einkaufsdatum.dateChanged.connect(self._schedule_filter_update)
                if self.filter_einkaufsdatum.lineEdit():
                        self.filter_einkaufsdatum.lineEdit().textChanged.connect(self._schedule_filter_update)
                self.filter_zuweisungsdatum.dateChanged.connect(self._schedule_filter_update)
                if self.filter_zuweisungsdatum.lineEdit():
                        self.filter_zuweisungsdatum.lineEdit().textChanged.connect(self._schedule_filter_update)
                self.add_owner_button.clicked.connect(self._add_owner_filter_value)

                selection_model = self.table.selectionModel()
                if selection_model:
                        selection_model.selectionChanged.connect(self._update_item_action_visibility)

                self._update_item_action_visibility()

        # ---------- Daten laden & Status ----------
        def _load_items(self) -> None:
                self.items = self.repository.list()
                self.custom_manufacturers = self.repository.list_custom_values(CUSTOM_CATEGORY_MANUFACTURER)
                self.custom_models = self.repository.list_custom_values(CUSTOM_CATEGORY_MODEL)
                self.custom_serial_numbers = self.repository.list_custom_values(CUSTOM_CATEGORY_SERIAL)
                self.custom_owners = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                self.filtered_items = list(self.items)
                self.table_model.set_items(self.filtered_items)
                self._refresh_object_types()
                self._update_object_type_filter()
                self._update_manufacturer_filter()
                self._update_model_filter()
                self._update_serial_filter()
                self._update_owner_combo()
                self._update_status()
                self._update_item_action_visibility()

        def _update_status(self) -> None:
                total = len(self.items)
                shown = len(self.filtered_items)
                self.statusBar().showMessage(f"Einträge: {shown} / {total}")

        def _update_item_action_visibility(self) -> None:
                selection_model = self.table.selectionModel()
                has_selection = False
                if selection_model:
                        has_selection = bool(selection_model.selectedRows())

                self.edit_action.setEnabled(has_selection)
                self.delete_action.setEnabled(has_selection)

        # ---------- Hilfen für Combos ----------
        def _merge_custom_values(self, base: Iterable[str], custom: Iterable[str]) -> List[str]:
                merged = {v.strip() for v in base if v and str(v).strip()}
                merged.update({v.strip() for v in custom if v and str(v).strip()})
                merged.discard('')
                return sorted(merged, key=str.casefold)

        def _refresh_object_types(self) -> None:
                self.object_types = self.settings.load_object_types()

        def _update_owner_combo(self) -> None:
                if not hasattr(self, 'filter_besitzer'):
                        return
                owners = self.repository.distinct_owners() if hasattr(self.repository, 'distinct_owners') else []
                owners = self._merge_custom_values(owners, self.custom_owners)
                current_text = self.filter_besitzer.currentText().strip() if self.filter_besitzer.count() else ''
                self.filter_besitzer.blockSignals(True)
                self.filter_besitzer.clear()
                self.filter_besitzer.addItem('')
                self.filter_besitzer.addItems(owners)
                if current_text:
                        self.filter_besitzer.setCurrentText(current_text)
                else:
                        self.filter_besitzer.setCurrentIndex(0)
                self.filter_besitzer.blockSignals(False)

        def _update_manufacturer_filter(self) -> None:
                if not hasattr(self, 'filter_hersteller'):
                        return
                manufacturers = self.repository.distinct_manufacturers() if hasattr(self.repository, 'distinct_manufacturers') else []
                manufacturers = self._merge_custom_values(manufacturers, self.custom_manufacturers)
                current_text = self.filter_hersteller.currentText().strip() if self.filter_hersteller.count() else ''
                self.filter_hersteller.blockSignals(True)
                self.filter_hersteller.clear()
                self.filter_hersteller.addItem('')
                self.filter_hersteller.addItems(manufacturers)
                if current_text:
                        self.filter_hersteller.setCurrentText(current_text)
                else:
                        self.filter_hersteller.setCurrentIndex(0)
                self.filter_hersteller.blockSignals(False)

        def _update_model_filter(self) -> None:
                if not hasattr(self, 'filter_modell'):
                        return
                models = self.repository.distinct_models() if hasattr(self.repository, 'distinct_models') else []
                models = self._merge_custom_values(models, self.custom_models)
                current_text = self.filter_modell.currentText().strip() if self.filter_modell.count() else ''
                self.filter_modell.blockSignals(True)
                self.filter_modell.clear()
                self.filter_modell.addItem('')
                self.filter_modell.addItems(models)
                if current_text:
                        self.filter_modell.setCurrentText(current_text)
                else:
                        self.filter_modell.setCurrentIndex(0)
                self.filter_modell.blockSignals(False)

        def _update_serial_filter(self) -> None:
                if not hasattr(self, 'filter_seriennummer'):
                        return
                serials = self.repository.distinct_serial_numbers() if hasattr(self.repository, 'distinct_serial_numbers') else []
                serials = self._merge_custom_values(serials, self.custom_serial_numbers)
                current_text = self.filter_seriennummer.currentText().strip() if self.filter_seriennummer.count() else ''
                self.filter_seriennummer.blockSignals(True)
                self.filter_seriennummer.clear()
                self.filter_seriennummer.addItem('')
                self.filter_seriennummer.addItems(serials)
                if current_text:
                        self.filter_seriennummer.setCurrentText(current_text)
                else:
                        self.filter_seriennummer.setCurrentIndex(0)
                self.filter_seriennummer.blockSignals(False)

        def _update_object_type_filter(self) -> None:
                if not hasattr(self, 'filter_objekttyp'):
                        return
                self._refresh_object_types()
                types_list = [t for t in self.object_types if t and str(t).strip()]
                current_text = self.filter_objekttyp.currentText().strip() if self.filter_objekttyp.count() else ''
                self.filter_objekttyp.blockSignals(True)
                self.filter_objekttyp.clear()
                self.filter_objekttyp.addItem('')
                self.filter_objekttyp.addItems(sorted(types_list, key=str.casefold))
                if current_text:
                        self.filter_objekttyp.setCurrentText(current_text)
                else:
                        self.filter_objekttyp.setCurrentIndex(0)
                self.filter_objekttyp.blockSignals(False)

        def _collect_item_dialog_values(self) -> tuple[list[str], list[str], list[str], list[str]]:
                repo_object_types = []
                if hasattr(self.repository, 'distinct_object_types'):
                        repo_object_types = self.repository.distinct_object_types()
                self._refresh_object_types()
                object_types = self._merge_custom_values(repo_object_types, self.object_types)

                repo_manufacturers = []
                if hasattr(self.repository, 'distinct_manufacturers'):
                        repo_manufacturers = self.repository.distinct_manufacturers()
                manufacturers = self._merge_custom_values(repo_manufacturers, self.custom_manufacturers)

                repo_models = []
                if hasattr(self.repository, 'distinct_models'):
                        repo_models = self.repository.distinct_models()
                models = self._merge_custom_values(repo_models, self.custom_models)

                repo_owners = []
                if hasattr(self.repository, 'distinct_owners'):
                        repo_owners = self.repository.distinct_owners()
                owners = self._merge_custom_values(repo_owners, self.custom_owners)

                return object_types, manufacturers, models, owners

        # ---------- Filter/ Suche ----------
        def _handle_search_submit(self) -> None:
                self.apply_filters()

        def _handle_search_text_change(self, text: str) -> None:
                self._schedule_filter_update()

        def _schedule_filter_update(self, *_args) -> None:
                if hasattr(self, '_filter_timer') and self._filter_timer:
                        self._filter_timer.stop()
                        self._filter_timer.start()

        def _date_text_or_empty(self, date_edit: QDateEdit) -> str:
                # get the plain text from the line edit; if empty, treat as no filter
                if date_edit and date_edit.lineEdit():
                        t = date_edit.lineEdit().text().strip()
                        return t
                return ''

        def _normalize_date(self, text: str) -> Optional[str]:
                if not text:
                        return None
                # Accept display format and convert to ISO yyyy-mm-dd
                try:
                        dt = datetime.strptime(text, DATE_FORMAT_DISPLAY)
                        return dt.strftime('%Y-%m-%d')
                except Exception:
                        try:
                                dt = datetime.strptime(text, DATE_FORMAT_QT_DISPLAY)
                                return dt.strftime('%Y-%m-%d')
                        except Exception:
                                return None

        def apply_filters(self) -> None:
                q = self.search_field.text().strip().lower()
                f_type = self.filter_objekttyp.currentText().strip().lower()
                f_man = self.filter_hersteller.currentText().strip().lower()
                f_model = self.filter_modell.currentText().strip().lower()
                f_serial = self.filter_seriennummer.currentText().strip().lower()
                f_owner = self.filter_besitzer.currentText().strip().lower()
                f_notes = self.filter_anmerkungen.text().strip().lower()

                buy_text = self._date_text_or_empty(self.filter_einkaufsdatum)
                assign_text = self._date_text_or_empty(self.filter_zuweisungsdatum)
                buy_iso = self._normalize_date(buy_text) if buy_text else None
                assign_iso = self._normalize_date(assign_text) if assign_text else None

                def match_text(val: Optional[str], needle: str) -> bool:
                        if not needle:
                                return True
                        return (val or '').strip().lower().find(needle) != -1

                filtered: List[Item] = []
                for it in self.items:
                        if f_type and (it.objekttyp or '').strip().lower() != f_type:
                                continue
                        if f_man and (it.hersteller or '').strip().lower() != f_man:
                                continue
                        if f_model and (it.modell or '').strip().lower() != f_model:
                                continue
                        if f_serial and (it.seriennummer or '').strip().lower() != f_serial:
                                continue
                        if f_owner and (it.aktueller_besitzer or '').strip().lower() != f_owner:
                                continue
                        if f_notes and not match_text(it.anmerkungen, f_notes):
                                continue
                        if buy_iso and (it.einkaufsdatum or '') != buy_iso:
                                continue
                        if assign_iso and (it.zuweisungsdatum or '') != assign_iso:
                                continue
                        if q:
                                haystack = ' '.join([
                                        it.objekttyp or '', it.hersteller or '', it.modell or '', it.seriennummer or '',
                                        it.einkaufsdatum or '', it.zuweisungsdatum or '', it.aktueller_besitzer or '',
                                        it.anmerkungen or ''
                                ]).lower()
                                if q not in haystack:
                                        continue
                        filtered.append(it)

                self.filtered_items = filtered
                self.table_model.set_items(self.filtered_items)
                self._update_status()

        def reset_filters(self) -> None:
                self.search_field.clear()
                for combo in (self.filter_objekttyp, self.filter_hersteller, self.filter_modell, self.filter_seriennummer, self.filter_besitzer):
                        combo.setCurrentIndex(0)
                        combo.setEditText('')
                for d in (self.filter_einkaufsdatum, self.filter_zuweisungsdatum):
                        if d.lineEdit():
                                d.lineEdit().setText('')
                self.filter_anmerkungen.clear()
                self.filtered_items = list(self.items)
                self.table_model.set_items(self.filtered_items)
                self._update_status()

        # ---------- Zoom/Font ----------
        def _adjust_font_size(self, delta: int) -> None:
                self._font_size = max(7, min(24, self._font_size + delta))
                f = QFont()
                f.setPointSize(self._font_size)
                self.table.setFont(f)
                self.table.resizeRowsToContents()
                self.table.resizeColumnsToContents()
                try:
                        if hasattr(self.settings, 'save_table'):
                                self.settings.save_table(self.table, self._font_size)
                except Exception:
                        pass

        # ---------- CRUD ----------
        def _current_row_index(self) -> Optional[int]:
                sel = self.table.selectionModel()
                if not sel:
                        return None
                rows = sel.selectedRows()
                if not rows:
                        return None
                return rows[0].row()

        def _selected_item(self) -> Optional[Item]:
                idx = self._current_row_index()
                if idx is None:
                        return None
                return self.table_model.item_at(idx)

        def create_item(self) -> None:
                object_types, manufacturers, models, owners = self._collect_item_dialog_values()
                dialog = ItemDialog(
                        self,
                        item=None,
                        owners=owners,
                        object_types=object_types,
                        manufacturers=manufacturers,
                        models=models,
                )
                result = dialog.exec()
                if result and dialog.result_action == ItemDialog.ACTION_SAVE:
                        new_item = dialog.get_item()
                        try:
                                if hasattr(self.repository, 'create'):
                                        self.repository.create(new_item)
                                else:
                                        self.repository.add(new_item)
                        except RepositoryError as e:
                                QMessageBox.critical(self, 'Fehler', f'Konnte Eintrag nicht speichern:\n{e}')
                                return
                        self._load_items()
                        self.reset_filters()

        def edit_selected_item(self) -> None:
                item = self._selected_item()
                if not item:
                        return
                object_types, manufacturers, models, owners = self._collect_item_dialog_values()
                dialog = ItemDialog(
                        self,
                        item=item,
                        owners=owners,
                        object_types=object_types,
                        manufacturers=manufacturers,
                        models=models,
                )
                result = dialog.exec()
                if dialog.result_action == ItemDialog.ACTION_DELETE:
                        self._delete_item(item)
                        return
                if result and dialog.result_action == ItemDialog.ACTION_SAVE:
                        updated = dialog.get_item()
                        item_id = item.id or updated.id
                        if item_id is None:
                                QMessageBox.critical(self, 'Fehler', 'Aktualisierung fehlgeschlagen:\nObjekt-ID fehlt.')
                                return
                        try:
                                self.repository.update(item_id, updated)
                        except TypeError:
                                # Fallback für Repositories mit älterer Signatur
                                self.repository.update(updated)
                        except AttributeError:
                                # Letzter Fallback falls nur eine add/create-Methode existiert
                                if hasattr(self.repository, 'create'):
                                        self.repository.create(updated)
                                else:
                                        self.repository.add(updated)
                        except RepositoryError as e:
                                QMessageBox.critical(self, 'Fehler', f'Aktualisierung fehlgeschlagen:\n{e}')
                                return
                        self._load_items()
                        self.reset_filters()

        def delete_selected_item(self) -> None:
                item = self._selected_item()
                if not item:
                        return
                self._delete_item(item)

        def _delete_item(self, item: Item) -> None:
                if QMessageBox.question(self, 'Löschen', 'Diesen Eintrag wirklich löschen?') != QMessageBox.Yes:
                        return
                item_id = item.id
                if item_id is None:
                        QMessageBox.critical(self, 'Fehler', 'Löschen fehlgeschlagen:\nObjekt-ID fehlt.')
                        return
                try:
                        self.repository.delete(item_id)
                except TypeError:
                        self.repository.delete(item)
                except RepositoryError as e:
                        QMessageBox.critical(self, 'Fehler', f'Löschen fehlgeschlagen:\n{e}')
                        return
                self._load_items()
                self.apply_filters()

        def _deactivate_item(self, item: Item) -> None:
                item_id = item.id
                if item_id is None:
                        QMessageBox.critical(self, 'Fehler', 'Stilllegen fehlgeschlagen:\nObjekt-ID fehlt.')
                        return
                try:
                        if hasattr(self.repository, 'deactivate'):
                                try:
                                        self.repository.deactivate(item_id)
                                except TypeError:
                                        self.repository.deactivate(item)
                        else:
                                setattr(item, 'stillgelegt', True)
                                try:
                                        self.repository.update(item_id, item)
                                except TypeError:
                                        self.repository.update(item)
                                except AttributeError:
                                        if hasattr(self.repository, 'create'):
                                                self.repository.create(item)
                                        else:
                                                self.repository.add(item)
                except RepositoryError as e:
                        QMessageBox.critical(self, 'Fehler', f'Stilllegen fehlgeschlagen:\n{e}')
                        return
                self._load_items()
                self.apply_filters()

        def deactivate_selected_item(self) -> None:
                item = self._selected_item()
                if not item:
                        return
                self._deactivate_item(item)

        # ---------- Export / Drucken ----------
        def _pick_export_path(self, suffix: str, filter_str: str) -> Optional[Path]:
                fn, _ = QFileDialog.getSaveFileName(self, 'Exportieren', f'inventar.{suffix}', filter_str)
                return Path(fn) if fn else None

        def export_data(self, fmt: str) -> None:
                data = self.filtered_items
                try:
                        if fmt == 'xlsx':
                                path = self._pick_export_path('xlsx', 'Excel (*.xlsx)')
                                if not path:
                                        return
                                export_to_xlsx(data, path)
                        elif fmt == 'csv':
                                path = self._pick_export_path('csv', 'CSV (*.csv)')
                                if not path:
                                        return
                                export_to_csv(data, path)
                        elif fmt == 'json':
                                path = self._pick_export_path('json', 'JSON (*.json)')
                                if not path:
                                        return
                                export_to_json(data, path)
                        else:
                                QMessageBox.warning(self, 'Export', f'Unbekanntes Format: {fmt}')
                                return
                except Exception as e:
                        QMessageBox.critical(self, 'Export', f'Export fehlgeschlagen:\n{e}')
                        return
                self.statusBar().showMessage('Export erfolgreich', 4000)

        def print_preview(self) -> None:
                items = list(self.filtered_items)
                if not items:
                        QMessageBox.information(self, 'Drucken', 'Keine Einträge zum Drucken vorhanden.')
                        return

                try:
                        self.printer.print_dialog(items, len(items))
                except Exception as e:
                        QMessageBox.critical(self, 'Drucken', f'Druck fehlgeschlagen:\n{e}')

        # ---------- Objekt-/Eigenschaftswerte pflegen ----------
        def _add_value_via_dialog(self, title: str, label: str) -> Optional[str]:
                text, ok = QInputDialog.getText(self, title, label)
                if ok:
                        text = text.strip()
                        return text or None
                return None

        def _add_owner_filter_value(self) -> None:
                val = self._add_value_via_dialog('Besitzer hinzufügen', 'Name:')
                if not val:
                        return
                try:
                        if hasattr(self.repository, 'add_custom_value'):
                                self.repository.add_custom_value(CUSTOM_CATEGORY_OWNER, val)
                        self.custom_owners = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                except Exception:
                        pass
                self._update_owner_combo()

        def _remove_owner_filter_value(self) -> None:
                val = self.filter_besitzer.currentText().strip()
                if not val:
                        return
                try:
                        if hasattr(self.repository, 'remove_custom_value'):
                                self.repository.remove_custom_value(CUSTOM_CATEGORY_OWNER, val)
                        self.custom_owners = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                except Exception:
                        pass
                self._update_owner_combo()


# ---------- Start/Run Helper ----------
def run() -> None:
        app = QApplication.instance() or QApplication([])
        w = MainWindow()
        w.show()
        app.exec()


if __name__ == '__main__':
        run()
