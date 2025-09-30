from __future__ import annotations

from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Iterable, List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QDate
from PySide6.QtGui import QAction, QIcon, QKeySequence, QColor
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
        background-color: #FFFFFF;
        color: #2C2C2C;
}

QWidget {
        background-color: #FFFFFF;
        color: #2C2C2C;
}

QLabel,
QStatusBar QLabel {
        color: #2C2C2C;
}

QGroupBox {
        background-color: #F2F2F2;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        margin-top: 12px;
        padding: 12px;
}

QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 4px;
        color: #006A8E;
}

QPushButton,
QToolButton {
        background-color: #00AEEF;
        color: #2C2C2C;
        border: none;
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 600;
}

QPushButton:hover,
QToolButton:hover {
        background-color: #1EB8F2;
}

QPushButton:pressed,
QToolButton:pressed {
        background-color: #0095C4;
}

QPushButton:disabled,
QToolButton:disabled {
        background-color: #F2F2F2;
        color: #9E9E9E;
}

QLineEdit,
QComboBox,
QDateEdit {
        background-color: #FFFFFF;
        border: 1px solid #D9D9D9;
        border-radius: 4px;
        padding: 4px 6px;
}

QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus {
        border: 1px solid #00AEEF;
}

QComboBox QAbstractItemView,
QDateEdit QAbstractItemView {
        background-color: #FFFFFF;
        border: 1px solid #D9D9D9;
        selection-background-color: #00AEEF;
        selection-color: #FFFFFF;
}

QTableView {
        background-color: #FFFFFF;
        alternate-background-color: #F2F2F2;
        gridline-color: #F2F2F2;
        border: 1px solid #E0E0E0;
        selection-background-color: #00AEEF;
        selection-color: #FFFFFF;
}

QTableView::item:selected {
        background-color: #00AEEF;
        color: #FFFFFF;
}

QHeaderView::section {
        background-color: #006A8E;
        color: #FFFFFF;
        padding: 8px;
        border: none;
        border-right: 1px solid #FFFFFF;
}

QTableCornerButton::section {
        background-color: #006A8E;
        border: none;
}

QStatusBar {
        background-color: #006A8E;
        color: #FFFFFF;
        border-top: 1px solid #F2F2F2;
}

QStatusBar QLabel {
        color: #FFFFFF;
}

QScrollBar:vertical,
QScrollBar:horizontal {
        background: #F2F2F2;
        border: none;
        border-radius: 4px;
        margin: 0px;
}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
        background: #00AEEF;
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
                self.object_types: List[str] = self.settings.load_object_types()
                self.repository, self.using_json_fallback = create_repository(Path.cwd())
                self.table_model = ItemTableModel()
                self.table = QTableView()
                self.table.setModel(self.table_model)
                self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
                self.table.setSelectionMode(QAbstractItemView.SingleSelection)
                self.table.doubleClicked.connect(self.edit_selected_item)
                self.table.setSortingEnabled(True)
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
                self.table.setAlternatingRowColors(True)

                self.printer = TablePrinter(self)

                self._font_size = 10
                self.items: List[Item] = []
                self.custom_manufacturers: list[str] = []
                self.custom_models: list[str] = []
                self.custom_serial_numbers: list[str] = []

                self._build_ui()
                self._apply_color_palette()
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
                layout.addWidget(self._build_form_filters())

                actions_layout = QHBoxLayout()
                self.new_button = QPushButton('Neues Objekt')
                self.edit_button = QPushButton('Bearbeiten')
                self.delete_button = QPushButton('Löschen')
                self.deactivate_button = QPushButton('Stilllegen')
                self.reset_button = QPushButton('Reset')
                self.export_excel_button = QPushButton('Excel')
                self.export_csv_button = QPushButton('CSV')
                self.export_json_button = QPushButton('JSON')
                self.print_button = QPushButton()
                self.print_button.setIcon(QIcon.fromTheme('document-print'))
                self.print_button.setToolTip('Drucken (Ctrl+P)')

                actions_layout.addWidget(self.new_button)
                actions_layout.addWidget(self.edit_button)
                actions_layout.addWidget(self.delete_button)
                actions_layout.addWidget(self.deactivate_button)

                layout.addLayout(actions_layout)
                layout.addWidget(self.table)

                zoom_layout = QHBoxLayout()
                self.zoom_in_button = QToolButton()
                self.zoom_in_button.setText('+')
                self.zoom_out_button = QToolButton()
                self.zoom_out_button.setText('−')
                zoom_layout.addWidget(QLabel('Zoom'))
                zoom_layout.addWidget(self.zoom_in_button)
                zoom_layout.addWidget(self.zoom_out_button)
                zoom_layout.addWidget(self.reset_button)

                bottom_layout = QHBoxLayout()
                export_layout = QHBoxLayout()
                export_layout.addWidget(self.export_excel_button)
                export_layout.addWidget(self.export_csv_button)
                export_layout.addWidget(self.export_json_button)
                export_layout.addWidget(self.print_button)

                bottom_layout.addLayout(export_layout)
                bottom_layout.addStretch()
                bottom_layout.addLayout(zoom_layout)
                layout.addLayout(bottom_layout)

                self.status_bar = QStatusBar()
                self.setStatusBar(self.status_bar)

                self.setCentralWidget(central)

        def _apply_color_palette(self) -> None:
                """Apply the corporate color palette to the main window widgets."""
                self.setStyleSheet(PALETTE_STYLESHEET)

        def _build_search_box(self) -> QWidget:
                box = QGroupBox('Suchen')
                layout = QHBoxLayout(box)
                self.search_field = QLineEdit()
                self.search_field.setPlaceholderText('In allen Feldern suchen ...')

                layout.addWidget(self.search_field)
                return box

        def _build_form_filters(self) -> QWidget:
                box = QGroupBox('Filter')
                layout = QHBoxLayout(box)

                left_layout = QFormLayout()
                self.filter_objekttyp = QComboBox()
                self.filter_objekttyp.setEditable(True)
                self.filter_objekttyp.setInsertPolicy(QComboBox.NoInsert)
                self.add_object_type_button = QToolButton()
                self.add_object_type_button.setText('+')
                self.add_object_type_button.setToolTip('Objekttyp zur Auswahlliste hinzufügen')
                self.remove_object_type_button = QToolButton()
                self.remove_object_type_button.setText('−')
                self.remove_object_type_button.setToolTip(
                        'Ausgewählten Objekttyp aus allen Einträgen entfernen'
                )
                object_type_layout = QHBoxLayout()
                object_type_layout.addWidget(self.filter_objekttyp)
                object_type_layout.addWidget(self.add_object_type_button)
                object_type_layout.addWidget(self.remove_object_type_button)
                object_type_layout.setContentsMargins(0, 0, 0, 0)
                object_type_layout.setSpacing(4)
                self._update_object_type_filter()

                self.filter_hersteller = QComboBox()
                self.filter_hersteller.setEditable(True)
                self.filter_hersteller.setInsertPolicy(QComboBox.NoInsert)
                self.add_manufacturer_button = QToolButton()
                self.add_manufacturer_button.setText('+')
                self.add_manufacturer_button.setToolTip('Hersteller zur Auswahlliste hinzufügen')
                self.remove_manufacturer_button = QToolButton()
                self.remove_manufacturer_button.setText('−')
                self.remove_manufacturer_button.setToolTip(
                        'Ausgewählten Hersteller aus allen Einträgen entfernen'
                )
                manufacturer_layout = QHBoxLayout()
                manufacturer_layout.addWidget(self.filter_hersteller)
                manufacturer_layout.addWidget(self.add_manufacturer_button)
                manufacturer_layout.addWidget(self.remove_manufacturer_button)
                manufacturer_layout.setContentsMargins(0, 0, 0, 0)
                manufacturer_layout.setSpacing(4)
                self._update_manufacturer_filter()

                self.filter_modell = QComboBox()
                self.filter_modell.setEditable(True)
                self.filter_modell.setInsertPolicy(QComboBox.NoInsert)
                self.add_model_button = QToolButton()
                self.add_model_button.setText('+')
                self.add_model_button.setToolTip('Modell zur Auswahlliste hinzufügen')
                self.remove_model_button = QToolButton()
                self.remove_model_button.setText('−')
                self.remove_model_button.setToolTip('Ausgewähltes Modell aus allen Einträgen entfernen')
                model_layout = QHBoxLayout()
                model_layout.addWidget(self.filter_modell)
                model_layout.addWidget(self.add_model_button)
                model_layout.addWidget(self.remove_model_button)
                model_layout.setContentsMargins(0, 0, 0, 0)
                model_layout.setSpacing(4)
                self._update_model_filter()

                self.filter_seriennummer = QComboBox()
                self.filter_seriennummer.setEditable(True)
                self.filter_seriennummer.setInsertPolicy(QComboBox.NoInsert)
                self.add_serial_button = QToolButton()
                self.add_serial_button.setText('+')
                self.add_serial_button.setToolTip('Seriennummer zur Auswahlliste hinzufügen')
                self.remove_serial_button = QToolButton()
                self.remove_serial_button.setText('−')
                self.remove_serial_button.setToolTip('Seriennummer aus allen Einträgen entfernen')
                serial_layout = QHBoxLayout()
                serial_layout.addWidget(self.filter_seriennummer)
                serial_layout.addWidget(self.add_serial_button)
                serial_layout.addWidget(self.remove_serial_button)
                serial_layout.setContentsMargins(0, 0, 0, 0)
                serial_layout.setSpacing(4)
                self._update_serial_filter()

                object_type_layout.setStretch(0, 1)

                left_layout.addRow('Objekttyp', object_type_layout)
                manufacturer_layout.setStretch(0, 1)
                left_layout.addRow('Hersteller', manufacturer_layout)
                model_layout.setStretch(0, 1)
                left_layout.addRow('Modell', model_layout)
                serial_layout.setStretch(0, 1)
                left_layout.addRow('Seriennummer', serial_layout)

                right_layout = QFormLayout()
                self.filter_einkaufsdatum = QDateEdit()
                # Qt benötigt ein eigenes Anzeigeformat, um die Datumswerte korrekt darzustellen.
                self.filter_einkaufsdatum.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
                self.filter_einkaufsdatum.setCalendarPopup(True)
                self.filter_einkaufsdatum.setSpecialValueText('')
                self.filter_einkaufsdatum.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
                self.filter_einkaufsdatum.setDate(QDate.currentDate())
                if self.filter_einkaufsdatum.lineEdit():
                        self.filter_einkaufsdatum.lineEdit().setText('')
                self.filter_zuweisungsdatum = QDateEdit()
                self.filter_zuweisungsdatum.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
                self.filter_zuweisungsdatum.setCalendarPopup(True)
                self.filter_zuweisungsdatum.setSpecialValueText('')
                self.filter_zuweisungsdatum.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
                self.filter_zuweisungsdatum.setDate(QDate.currentDate())
                if self.filter_zuweisungsdatum.lineEdit():
                        self.filter_zuweisungsdatum.lineEdit().setText('')
                self.filter_besitzer = QComboBox()
                self.filter_besitzer.setEditable(True)
                self.filter_besitzer.setInsertPolicy(QComboBox.NoInsert)
                self._update_owner_combo()
                self.filter_anmerkungen = QLineEdit()
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
                return box

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
                self.deactivate_button.clicked.connect(self.deactivate_selected_item)
                self.reset_button.clicked.connect(self.reset_filters)
                self.export_excel_button.clicked.connect(partial(self.export_data, 'xlsx'))
                self.export_csv_button.clicked.connect(partial(self.export_data, 'csv'))
                self.export_json_button.clicked.connect(partial(self.export_data, 'json'))
                self.print_button.clicked.connect(self.print_preview)

                self.zoom_in_button.clicked.connect(lambda: self._adjust_font_size(1))
                self.zoom_out_button.clicked.connect(lambda: self._adjust_font_size(-1))

                self.search_field.returnPressed.connect(self._handle_search_submit)

                self.add_object_type_button.clicked.connect(self._add_object_type_filter_value)
                self.remove_object_type_button.clicked.connect(self._remove_object_type_filter_value)
                self.add_manufacturer_button.clicked.connect(self._add_manufacturer_filter_value)
                self.remove_manufacturer_button.clicked.connect(self._remove_manufacturer_filter_value)
                self.add_model_button.clicked.connect(self._add_model_filter_value)
                self.remove_model_button.clicked.connect(self._remove_model_filter_value)
                self.add_serial_button.clicked.connect(self._add_serial_filter_value)
                self.remove_serial_button.clicked.connect(self._remove_serial_value)
                self.remove_owner_button.clicked.connect(self._remove_owner_filter_value)
                self.new_action.triggered.connect(self.create_item)
                self.edit_action.triggered.connect(self.edit_selected_item)
                self.delete_action.triggered.connect(self.delete_selected_item)
                self.search_action.triggered.connect(lambda: self.search_field.setFocus())
                self.print_action.triggered.connect(self.print_preview)

                if self.filter_hersteller.lineEdit():
                        self.filter_hersteller.lineEdit().returnPressed.connect(self.apply_filters)
                if self.filter_modell.lineEdit():
                        self.filter_modell.lineEdit().returnPressed.connect(self.apply_filters)
                if self.filter_seriennummer.lineEdit():
                        self.filter_seriennummer.lineEdit().returnPressed.connect(self.apply_filters)
                self.filter_anmerkungen.returnPressed.connect(self.apply_filters)
                if self.filter_objekttyp.lineEdit():
                        self.filter_objekttyp.lineEdit().returnPressed.connect(self.apply_filters)
                if self.filter_besitzer.lineEdit():
                        self.filter_besitzer.lineEdit().returnPressed.connect(self.apply_filters)
                self.add_owner_button.clicked.connect(self._add_owner_filter_value)

        def _load_items(self) -> None:
                self.items = self.repository.list()
                self.table_model.set_items(self.items)
                self._refresh_object_types()
                self._update_object_type_filter()
                self._update_manufacturer_filter()
                self._update_model_filter()
                self._update_serial_filter()
                self._update_owner_combo()
                self._update_status()

        def _update_owner_combo(self) -> None:
                if not hasattr(self, 'filter_besitzer'):
                        return
                owners = self.repository.distinct_owners()
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
                manufacturers = self.repository.distinct_manufacturers()
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
                models = self.repository.distinct_models()
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
                serials = self.repository.distinct_serial_numbers()
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

        @staticmethod
        def _merge_custom_values(values: list[str], custom_values: list[str]) -> list[str]:
                merged = list(values)
                existing = {value.lower() for value in merged}
                for custom in custom_values:
                        key = custom.lower()
                        if key not in existing:
                                merged.append(custom)
                                existing.add(key)
                return merged

        @staticmethod
        def _sorted_unique(values: Iterable[str]) -> list[str]:
                unique: dict[str, str] = {}
                for value in values:
                        text = str(value).strip()
                        if not text:
                                continue
                        key = text.casefold()
                        if key not in unique:
                                unique[key] = text
                return sorted(unique.values(), key=str.casefold)

        def _available_object_types(self) -> list[str]:
                return self._sorted_unique(self.object_types)

        def _available_manufacturers(self) -> list[str]:
                repo_values = self.repository.distinct_manufacturers()
                merged = self._merge_custom_values(repo_values, self.custom_manufacturers)
                return self._sorted_unique(merged)

        def _available_models(self) -> list[str]:
                repo_values = self.repository.distinct_models()
                merged = self._merge_custom_values(repo_values, self.custom_models)
                return self._sorted_unique(merged)

        def _available_owners(self) -> list[str]:
                repo_values = self.repository.distinct_owners()
                filter_values: list[str] = []
                if hasattr(self, 'filter_besitzer'):
                        filter_values = [
                                self.filter_besitzer.itemText(index)
                                for index in range(self.filter_besitzer.count())
                        ]
                return self._sorted_unique(list(repo_values) + filter_values)

        def _refresh_object_types(self) -> None:
                repo_types = self.repository.distinct_object_types()
                self.object_types = self.settings.sync_object_types(repo_types)

        def _update_object_type_filter(self) -> None:
                if not hasattr(self, 'filter_objekttyp'):
                        return
                current_text = self.filter_objekttyp.currentText().strip() if self.filter_objekttyp.count() else ''
                self.filter_objekttyp.blockSignals(True)
                self.filter_objekttyp.clear()
                self.filter_objekttyp.addItem('')
                self.filter_objekttyp.addItems(self.object_types)
                if current_text:
                        self.filter_objekttyp.setCurrentText(current_text)
                else:
                        self.filter_objekttyp.setCurrentIndex(0)
                self.filter_objekttyp.blockSignals(False)

        def _register_object_type(self, objekttyp: str) -> None:
                value = objekttyp.strip()
                if not value:
                        return
                self.object_types = self.settings.add_object_type(value)
                self._update_object_type_filter()

        def _add_object_type_filter_value(self) -> None:
                text, ok = QInputDialog.getText(self, 'Objekttyp hinzufügen', 'Neuen Objekttyp eingeben:')
                if not ok:
                        return
                value = text.strip()
                if not value:
                        return
                self.object_types = self.settings.add_object_type(value)
                self._update_object_type_filter()
                self.filter_objekttyp.setCurrentText(value)

        def _remove_object_type_filter_value(self) -> None:
                value = self.filter_objekttyp.currentText().strip()
                if not value:
                        QMessageBox.information(self, 'Eintrag entfernen', 'Bitte zuerst einen Objekttyp auswählen.')
                        return
                if QMessageBox.question(
                        self,
                        'Objekttyp entfernen',
                        f"Soll der Objekttyp '{value}' aus allen Einträgen entfernt werden?",
                ) != QMessageBox.Yes:
                        return
                try:
                        removed = self.repository.clear_object_type(value)
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Fehler', str(exc))
                        return
                remaining = [entry for entry in self.object_types if entry.lower() != value.lower()]
                self.object_types = self.settings.save_object_types(remaining)
                self._load_items()
                if self._has_active_filters():
                        self.apply_filters()
                message = (
                        f"{removed} Einträge ohne Objekttyp aktualisiert"
                        if removed
                        else 'Keine passenden Einträge gefunden'
                )
                self.statusBar().showMessage(message, 5000)
                self.filter_objekttyp.setCurrentIndex(0)

        def _add_manufacturer_filter_value(self) -> None:
                text, ok = QInputDialog.getText(self, 'Hersteller hinzufügen', 'Neuen Hersteller eingeben:')
                if not ok:
                        return
                value = text.strip()
                if not value:
                        return
                if value.lower() not in {entry.lower() for entry in self.custom_manufacturers}:
                        self.custom_manufacturers.append(value)
                if self.filter_hersteller.findText(value, Qt.MatchFixedString) == -1:
                        self.filter_hersteller.addItem(value)
                self._update_manufacturer_filter()
                self.filter_hersteller.setCurrentText(value)

        def _remove_manufacturer_filter_value(self) -> None:
                value = self.filter_hersteller.currentText().strip()
                if not value:
                        QMessageBox.information(self, 'Eintrag entfernen', 'Bitte zuerst einen Hersteller auswählen.')
                        return
                if QMessageBox.question(
                        self,
                        'Hersteller entfernen',
                        f"Soll der Hersteller '{value}' aus allen Einträgen entfernt werden?",
                ) != QMessageBox.Yes:
                        return
                try:
                        removed = self.repository.clear_manufacturer(value)
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Fehler', str(exc))
                        return
                self.custom_manufacturers = [entry for entry in self.custom_manufacturers if entry.lower() != value.lower()]
                self._load_items()
                if self._has_active_filters():
                        self.apply_filters()
                message = (
                        f"{removed} Einträge ohne Hersteller aktualisiert"
                        if removed
                        else 'Keine passenden Einträge gefunden'
                )
                self.statusBar().showMessage(message, 5000)
                self.filter_hersteller.setCurrentIndex(0)

        def _add_model_filter_value(self) -> None:
                text, ok = QInputDialog.getText(self, 'Modell hinzufügen', 'Neues Modell eingeben:')
                if not ok:
                        return
                value = text.strip()
                if not value:
                        return
                if value.lower() not in {entry.lower() for entry in self.custom_models}:
                        self.custom_models.append(value)
                if self.filter_modell.findText(value, Qt.MatchFixedString) == -1:
                        self.filter_modell.addItem(value)
                self._update_model_filter()
                self.filter_modell.setCurrentText(value)

        def _remove_model_filter_value(self) -> None:
                value = self.filter_modell.currentText().strip()
                if not value:
                        QMessageBox.information(self, 'Eintrag entfernen', 'Bitte zuerst ein Modell auswählen.')
                        return
                if QMessageBox.question(
                        self,
                        'Modell entfernen',
                        f"Soll das Modell '{value}' aus allen Einträgen entfernt werden?",
                ) != QMessageBox.Yes:
                        return
                try:
                        removed = self.repository.clear_model(value)
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Fehler', str(exc))
                        return
                self.custom_models = [entry for entry in self.custom_models if entry.lower() != value.lower()]
                self._load_items()
                if self._has_active_filters():
                        self.apply_filters()
                message = (
                        f"{removed} Einträge ohne Modell aktualisiert"
                        if removed
                        else 'Keine passenden Einträge gefunden'
                )
                self.statusBar().showMessage(message, 5000)
                self.filter_modell.setCurrentIndex(0)

        def _add_serial_filter_value(self) -> None:
                text, ok = QInputDialog.getText(self, 'Seriennummer hinzufügen', 'Seriennummer eingeben:')
                if not ok:
                        return
                value = text.strip()
                if not value:
                        return
                if value.lower() not in {entry.lower() for entry in self.custom_serial_numbers}:
                        self.custom_serial_numbers.append(value)
                if self.filter_seriennummer.findText(value, Qt.MatchFixedString) == -1:
                        self.filter_seriennummer.addItem(value)
                self._update_serial_filter()
                self.filter_seriennummer.setCurrentText(value)

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

        def _remove_owner_filter_value(self) -> None:
                value = self.filter_besitzer.currentText().strip()
                if not value:
                        QMessageBox.information(self, 'Eintrag entfernen', 'Bitte zuerst einen Besitzer auswählen.')
                        return
                if QMessageBox.question(
                        self,
                        'Besitzer entfernen',
                        f"Soll der Besitzer '{value}' aus allen Einträgen entfernt werden?",
                ) != QMessageBox.Yes:
                        return
                try:
                        removed = self.repository.clear_owner(value)
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Fehler', str(exc))
                        return
                self._load_items()
                if self._has_active_filters():
                        self.apply_filters()
                message = (
                        f'{removed} Einträge ohne Besitzer aktualisiert'
                        if removed
                        else 'Keine passenden Einträge gefunden'
                )
                self.statusBar().showMessage(message, 5000)
                self.filter_besitzer.setCurrentIndex(0)

        def _remove_serial_value(self) -> None:
                value = self.filter_seriennummer.currentText().strip()
                if not value:
                        current = self._current_item()
                        if current and current.seriennummer:
                                value = current.seriennummer
                        else:
                                QMessageBox.information(
                                        self,
                                        'Seriennummer entfernen',
                                        'Bitte geben Sie eine Seriennummer ein oder wählen Sie einen Eintrag aus.',
                                )
                                return
                if QMessageBox.question(
                        self,
                        'Seriennummer entfernen',
                        f"Soll die Seriennummer '{value}' aus allen Einträgen entfernt werden?",
                ) != QMessageBox.Yes:
                        return
                try:
                        removed = self.repository.clear_serial_number(value)
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Fehler', str(exc))
                        return
                self.custom_serial_numbers = [entry for entry in self.custom_serial_numbers if entry.lower() != value.lower()]
                self._update_serial_filter()
                self.filter_seriennummer.setCurrentIndex(0)
                if self.filter_seriennummer.lineEdit():
                        self.filter_seriennummer.lineEdit().clear()
                self._load_items()
                if self._has_active_filters():
                        self.apply_filters()
                message = (
                        f'{removed} Seriennummern entfernt'
                        if removed
                        else 'Keine Einträge mit dieser Seriennummer gefunden'
                )
                self.statusBar().showMessage(message, 5000)

        def _has_active_filters(self) -> bool:
                if self.search_field.text().strip():
                        return True

                widgets: list[QWidget] = [
                        self.filter_objekttyp,
                        self.filter_hersteller,
                        self.filter_modell,
                        self.filter_besitzer,
                        self.filter_anmerkungen,
                        self.filter_seriennummer,
                ]
                for widget in widgets:
                        if isinstance(widget, QComboBox):
                                if widget.currentText().strip():
                                        return True
                        elif widget.text().strip():  # type: ignore[union-attr]
                                return True

                for date_widget in [self.filter_einkaufsdatum, self.filter_zuweisungsdatum]:
                        if date_widget.text().strip():
                                return True

                return False

        def _update_status(self) -> None:
                total = len(self.table_model._items)
                self.statusBar().showMessage(f'Gesamtobjekte: {total}')

        def reset_filters(self) -> None:
                self.search_field.clear()
                self._clear_filter_inputs()
                self._load_items()

        def _handle_search_submit(self) -> None:
                """Reset the filter widgets before applying a global search."""
                self._clear_filter_inputs()
                self.apply_filters()

        def _clear_filter_inputs(self) -> None:
                """Clear all filter widgets without touching the search field."""
                self.filter_objekttyp.setCurrentIndex(0)
                self.filter_hersteller.setCurrentIndex(0)
                self.filter_modell.setCurrentIndex(0)
                self.filter_seriennummer.setCurrentIndex(0)
                self.filter_anmerkungen.clear()
                self.filter_besitzer.setCurrentIndex(0)
                if self.filter_objekttyp.lineEdit():
                        self.filter_objekttyp.lineEdit().clear()
                if self.filter_hersteller.lineEdit():
                        self.filter_hersteller.lineEdit().clear()
                if self.filter_modell.lineEdit():
                        self.filter_modell.lineEdit().clear()
                if self.filter_seriennummer.lineEdit():
                        self.filter_seriennummer.lineEdit().clear()
                if self.filter_einkaufsdatum.lineEdit():
                        self.filter_einkaufsdatum.lineEdit().setText('')
                if self.filter_zuweisungsdatum.lineEdit():
                        self.filter_zuweisungsdatum.lineEdit().setText('')

        def apply_filters(self) -> None:
                filters: dict[str, str] = {}
                status_message: str | None = None

                search_text = self.search_field.text().strip()
                if search_text:
                        filters['__global__'] = search_text

                def _widget_value(widget: QWidget) -> str:
                        if isinstance(widget, QComboBox):
                                return widget.currentText().strip()
                        return widget.text().strip()  # type: ignore[no-any-return]

                for widget, key in [
                        (self.filter_objekttyp, 'objekttyp'),
                        (self.filter_hersteller, 'hersteller'),
                        (self.filter_modell, 'modell'),
                        (self.filter_seriennummer, 'seriennummer'),
                        (self.filter_besitzer, 'aktueller_besitzer'),
                        (self.filter_anmerkungen, 'anmerkungen'),
                ]:
                        value = _widget_value(widget)
                        if value:
                                filters[key] = value

                for widget, key in [
                        (self.filter_einkaufsdatum, 'einkaufsdatum'),
                        (self.filter_zuweisungsdatum, 'zuweisungsdatum'),
                ]:
                        datums_text = widget.text().strip()
                        if not datums_text:
                                continue
                        try:
                                filters[key] = ItemValidator.convert_display_to_iso(datums_text)
                        except ValueError:
                                status_message = 'Ungültiges Datum im Filter – Format TT.MM.JJJJ verwenden.'

                self.items = self.repository.list(filters if filters else None)
                self.table_model.set_items(self.items)
                self._update_status()
                if status_message is None:
                        status_message = f'{len(self.items)} Einträge gefiltert'
                self.statusBar().showMessage(status_message, 5000)

        def _collect_dialog_data(self, dialog: ItemDialog) -> Item:
                data = dialog.get_item_data()
                return Item(
                        objekttyp=data['objekttyp'],
                        hersteller=data['hersteller'],
                        modell=data['modell'],
                        seriennummer=data['seriennummer'],
                        einkaufsdatum=data['einkaufsdatum'],
                        zuweisungsdatum=data['zuweisungsdatum'],
                        aktueller_besitzer=data['aktueller_besitzer'],
                        anmerkungen=data['anmerkungen'],
                        stillgelegt=dialog.item.stillgelegt if dialog.item else False,
                )

        def create_item(self) -> None:
                dialog = ItemDialog(
                        self,
                        owners=self._available_owners(),
                        object_types=self._available_object_types(),
                        manufacturers=self._available_manufacturers(),
                        models=self._available_models(),
                )
                if dialog.exec() == ItemDialog.Accepted:
                        item = self._collect_dialog_data(dialog)
                        try:
                                created = self.repository.create(item)
                        except RepositoryError as exc:
                                QMessageBox.critical(self, 'Fehler', str(exc))
                                return
                        self._register_object_type(created.objekttyp)
                        self._load_items()
                        self._select_item(created)
                        self.statusBar().showMessage('Objekt angelegt', 4000)

        def edit_selected_item(self) -> None:
                selected = self._current_item()
                if not selected:
                        return
                dialog = ItemDialog(
                        self,
                        item=selected,
                        owners=self._available_owners(),
                        object_types=self._available_object_types(),
                        manufacturers=self._available_manufacturers(),
                        models=self._available_models(),
                )
                if dialog.exec() != ItemDialog.Accepted:
                        return
                item_data = self._collect_dialog_data(dialog)
                try:
                        updated = self.repository.update(selected.id, item_data)  # type: ignore[arg-type]
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Fehler', str(exc))
                        return
                self._register_object_type(updated.objekttyp)
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

        def deactivate_selected_item(self) -> None:
                selected = self._current_item()
                if not selected:
                        return
                if QMessageBox.question(
                        self,
                        'Stilllegen bestätigen',
                        'Soll das ausgewählte Objekt stillgelegt werden?',
                ) != QMessageBox.Yes:
                        return
                if selected.id is None:
                        QMessageBox.warning(self, 'Stilllegen', 'Das Objekt besitzt keine gültige ID.')
                        return
                try:
                        # Visuelles Feedback, bevor der Eintrag aus der Tabelle entfernt wird
                        index_list = self.table.selectionModel().selectedRows()
                        if index_list:
                                row = index_list[0].row()
                                self.table_model._items[row] = selected.copy(stillgelegt=True)
                                top_left = self.table_model.index(row, 0)
                                bottom_right = self.table_model.index(row, len(COLUMN_KEYS) - 1)
                                self.table_model.dataChanged.emit(top_left, bottom_right, [Qt.ForegroundRole, Qt.BackgroundRole])
                        self.repository.deactivate(selected.id)
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Fehler', str(exc))
                        return
                self._load_items()
                self.statusBar().showMessage('Objekt stillgelegt', 4000)

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
